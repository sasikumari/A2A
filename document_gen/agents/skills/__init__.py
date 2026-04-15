"""
Skill-based agent framework — Claude-style tool/skill dispatch.

Every capability an agent has is expressed as a Skill with:
  - name          : unique snake_case identifier
  - description   : what the skill does (shown to the LLM)
  - parameters    : JSON Schema describing accepted arguments
  - execute()     : actual implementation

The LLM plans which skills to call (and with what args) given an intent.
The SkillExecutor runs the plan step-by-step and feeds results back.
"""

from __future__ import annotations
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Core data types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SkillResult:
    """Returned by every skill.execute() call."""
    success: bool
    output: Any = None          # primary payload (string, dict, list, …)
    error: str | None = None    # human-readable error if success=False
    metadata: dict = field(default_factory=dict)  # extra info (size, path, …)

    def __repr__(self):
        if self.success:
            out_repr = str(self.output)[:120] if self.output else "—"
            return f"<SkillResult OK: {out_repr}>"
        return f"<SkillResult ERROR: {self.error}>"


@dataclass
class SkillCall:
    """One step in an LLM-generated skill plan."""
    skill_name: str
    arguments: dict
    reason: str = ""            # LLM's explanation for why this skill is needed
    step: int = 0

    def to_dict(self):
        return {
            "step": self.step,
            "skill": self.skill_name,
            "args": self.arguments,
            "reason": self.reason,
        }


@dataclass
class SkillExecution:
    """Record of one skill execution (call + result + timing)."""
    call: SkillCall
    result: SkillResult
    elapsed_ms: float

    def to_dict(self):
        return {
            **self.call.to_dict(),
            "success": self.result.success,
            "output_summary": str(self.result.output)[:200] if self.result.output else None,
            "error": self.result.error,
            "elapsed_ms": round(self.elapsed_ms),
        }


@dataclass
class PlanResult:
    """Full result of executing a skill plan."""
    success: bool
    executions: list[SkillExecution] = field(default_factory=list)
    final_output: Any = None
    error: str | None = None

    @property
    def steps_ok(self):
        return sum(1 for e in self.executions if e.result.success)

    @property
    def steps_failed(self):
        return sum(1 for e in self.executions if not e.result.success)

    def summary(self):
        return (
            f"{'OK' if self.success else 'FAILED'} — "
            f"{self.steps_ok}/{len(self.executions)} steps passed"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Skill base class
# ─────────────────────────────────────────────────────────────────────────────

class Skill(ABC):
    """
    Base class for all agent skills.

    Subclasses must define:
      - name        (class attribute)
      - description (class attribute)
      - parameters  (class attribute — JSON Schema dict)
      - execute(**kwargs) -> SkillResult
    """

    name: str = ""
    description: str = ""
    # JSON Schema for inputs — shown to the LLM so it knows what to pass
    parameters: dict = {}

    @abstractmethod
    def execute(self, **kwargs) -> SkillResult:
        ...

    def to_tool_spec(self) -> dict:
        """Serialise to Claude-style tool spec for LLM prompt injection."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    def __repr__(self):
        return f"<Skill:{self.name}>"


# ─────────────────────────────────────────────────────────────────────────────
# Skill Registry
# ─────────────────────────────────────────────────────────────────────────────

class SkillRegistry:
    """Global registry — agents register skills here; planner queries it."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill):
        self._skills[skill.name] = skill
        return self  # fluent

    def register_many(self, skills: list[Skill]):
        for s in skills:
            self.register(s)
        return self

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def all(self) -> list[Skill]:
        return list(self._skills.values())

    def names(self) -> list[str]:
        return list(self._skills.keys())

    def to_tool_specs(self) -> list[dict]:
        """Return all skills as LLM tool specs."""
        return [s.to_tool_spec() for s in self._skills.values()]

    def __repr__(self):
        return f"<SkillRegistry [{', '.join(self.names())}]>"


# ─────────────────────────────────────────────────────────────────────────────
# Skill Executor
# ─────────────────────────────────────────────────────────────────────────────

class SkillExecutor:
    """
    Runs a list of SkillCalls against a registry.

    Supports:
      - Sequential execution with result chaining
      - Stop-on-failure or continue-on-failure mode
      - Event bus publishing for live UI updates
    """

    def __init__(
        self,
        registry: SkillRegistry,
        bus=None,
        agent_name: str = "Agent",
        stop_on_failure: bool = False,
    ):
        self.registry = registry
        self.bus = bus
        self.agent_name = agent_name
        self.stop_on_failure = stop_on_failure

    def _publish(self, status: str, msg: str, extra: dict | None = None):
        if not self.bus:
            return
        event = {"name": self.agent_name, "status": status, "msg": msg}
        if extra:
            event.update(extra)
        self.bus.publish_event("agent_status", event)

    def run(self, plan: list[SkillCall], context: dict | None = None) -> PlanResult:
        """
        Execute each SkillCall in sequence.
        context: mutable dict shared across all steps (skills can read/write it).
        """
        if context is None:
            context = {}

        executions: list[SkillExecution] = []

        for call in plan:
            skill = self.registry.get(call.skill_name)
            if skill is None:
                err = f"Unknown skill: {call.skill_name}"
                self._publish("ERROR", err)
                result = SkillResult(success=False, error=err)
                executions.append(SkillExecution(call=call, result=result, elapsed_ms=0))
                if self.stop_on_failure:
                    return PlanResult(success=False, executions=executions, error=err)
                continue

            self._publish(
                "ACTION",
                f"[{call.step}] {skill.name} — {call.reason or skill.description}",
                {"skill": call.skill_name, "args": call.arguments},
            )

            t0 = time.monotonic()
            try:
                # Inject shared context as _context kwarg if skill accepts it
                args = dict(call.arguments)
                args["_context"] = context
                result = skill.execute(**args)
            except Exception as exc:
                result = SkillResult(success=False, error=str(exc))

            elapsed_ms = (time.monotonic() - t0) * 1000
            exec_record = SkillExecution(call=call, result=result, elapsed_ms=elapsed_ms)
            executions.append(exec_record)

            # Store result in shared context under skill name for downstream steps
            context[f"result_{call.skill_name}_{call.step}"] = result

            status = "ACTION_OK" if result.success else "ACTION_FAIL"
            self._publish(
                status,
                f"[{call.step}] {skill.name} → {'OK' if result.success else result.error}",
                {"elapsed_ms": round(elapsed_ms)},
            )

            if not result.success and self.stop_on_failure:
                return PlanResult(
                    success=False,
                    executions=executions,
                    error=f"Step {call.step} ({call.skill_name}) failed: {result.error}",
                )

        final_success = all(e.result.success for e in executions)
        # Last successful output is the final output
        final_output = next(
            (e.result.output for e in reversed(executions) if e.result.success),
            None,
        )
        return PlanResult(
            success=final_success,
            executions=executions,
            final_output=final_output,
        )
