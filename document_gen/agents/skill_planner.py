"""
SkillPlanner — LLM-powered planner that decides which skills to call.

Given:
  - An intent (user request / spec change)
  - A SkillRegistry (list of available skills with their schemas)
  - Optional context (current file contents, previous errors, etc.)

The planner asks the LLM to produce an ordered list of SkillCall objects
— exactly like Claude's tool_use blocks — then returns that plan for
the SkillExecutor to run.
"""

from __future__ import annotations
import json
import re
from .skills import SkillCall, SkillRegistry


# ─────────────────────────────────────────────────────────────────────────────
# Planner
# ─────────────────────────────────────────────────────────────────────────────

class SkillPlanner:
    """
    Uses the LLM to convert an intent into an ordered SkillCall plan.

    The LLM sees each skill as a "tool" with name + description + input_schema
    (same format as Claude's tool_choice/tool_use API).
    """

    SYSTEM = """You are an expert agentic orchestrator for an NPCI UPI payment system.
Your job: given an intent and a list of available actions, produce the EXACT sequence
of action calls needed to accomplish the intent safely and correctly.

RULES:
1. Always read a file before writing or patching it.
2. Always backup a file before writing or patching it.
3. After writing/patching, always verify (syntax_check + truncation_check + xsd_validate if XSD).
4. If verification fails after a write, call rollback_file, then retry with a new generate_code_update.
5. For limit changes (P2P/MAX_TXN_AMOUNT) — ONLY modify switch/upi_switch.py. Never touch XSD.
6. For new XML fields — only add OPTIONAL elements to upi_pay_request.xsd.
7. Always run run_tests and hot_reload after all file changes.
8. Always end with create_backup_snapshot and git_commit.

Return ONLY a JSON array of action calls. No prose, no markdown fences.
Each element:
{
  "step": <integer starting at 1>,
  "action": "<action_name>",
  "args": { <action arguments matching the action's input_schema> },
  "reason": "<one sentence why this step is needed>"
}

Available actions and their schemas are listed below.
"""

    def __init__(self, llm_client, registry: SkillRegistry):
        self.llm_client = llm_client
        self.registry = registry

    def plan(
        self,
        intent: str,
        context: dict | None = None,
        managed_files: list[str] | None = None,
        previous_error: str | None = None,
    ) -> list[SkillCall]:
        """
        Ask the LLM to produce a skill plan for the given intent.

        context: optional dict with extra info (e.g. current file contents preview)
        managed_files: list of file paths this agent is responsible for
        previous_error: if a previous plan failed, pass the error here for retry
        """
        tools_spec = json.dumps(self.registry.to_tool_specs(), indent=2)

        context_block = ""
        if context:
            context_block = "\n\nCONTEXT:\n" + json.dumps(context, indent=2)[:3000]

        files_block = ""
        if managed_files:
            files_block = "\n\nFILES THIS AGENT MANAGES:\n" + "\n".join(f"  - {f}" for f in managed_files)

        error_block = ""
        if previous_error:
            error_block = f"\n\nPREVIOUS ATTEMPT FAILED WITH:\n{previous_error}\nAdjust the plan to fix this."

        prompt = (
            f"{self.SYSTEM}\n\n"
            f"AVAILABLE SKILLS:\n{tools_spec}"
            f"{files_block}"
            f"{context_block}"
            f"{error_block}\n\n"
            f"INTENT: {intent}\n\n"
            f"Return the skill call plan as a JSON array:"
        )

        raw = self.llm_client.query(prompt)
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        return self._parse_plan(raw)

    def plan_file_update(
        self,
        file_path: str,
        spec_change: str,
        project_root: str,
        version: str = "1.x",
        previous_error: str | None = None,
    ) -> list[SkillCall]:
        """
        Convenience method: plan the full skill sequence to update one file.
        Uses a deterministic template plan + LLM customization.
        """
        file_type = "xsd" if file_path.endswith((".xsd", ".xml")) else "python"

        # Template: backup → read → generate → write → verify → (rollback on fail)
        # The LLM can add extra steps (search_codebase, explain_change, etc.)
        intent = (
            f"Update {file_path} to implement: {spec_change}\n"
            f"Project root: {project_root}\n"
            f"Version: {version}\n"
            f"File type: {file_type}"
        )
        return self.plan(
            intent=intent,
            managed_files=[file_path],
            previous_error=previous_error,
        )

    def _parse_plan(self, raw: str) -> list[SkillCall]:
        """Parse the LLM's JSON array into SkillCall objects."""
        # Find JSON array
        start = raw.find('[')
        end = raw.rfind(']')
        if start == -1 or end == -1:
            print(f"[SkillPlanner] No JSON array found in LLM response. Falling back to empty plan.")
            return []

        try:
            items = json.loads(raw[start:end + 1])
        except json.JSONDecodeError as e:
            print(f"[SkillPlanner] JSON parse error: {e}. Raw: {raw[start:start+500]}")
            return []

        calls = []
        for item in items:
            if not isinstance(item, dict):
                continue
            skill_name = item.get("skill") or item.get("action") or item.get("name") or item.get("skill_name")
            args = item.get("args") or item.get("arguments") or item.get("input") or {}
            reason = item.get("reason") or item.get("description") or ""
            step = item.get("step", len(calls) + 1)

            if not skill_name:
                continue

            # Validate action exists
            if self.registry.get(skill_name) is None:
                print(f"[SkillPlanner] WARNING: Action '{skill_name}' not in registry — skipping.")
                continue

            calls.append(SkillCall(
                skill_name=skill_name,
                arguments=args if isinstance(args, dict) else {},
                reason=str(reason),
                step=int(step),
            ))

        return calls

    def build_deterministic_plan(
        self,
        file_path: str,
        spec_change: str,
        project_root: str,
        version: str = "1.x",
    ) -> list[SkillCall]:
        """
        Fallback: build a safe, hardcoded plan without LLM.
        Used when the LLM planner fails or for guaranteed correctness.
        """
        is_xsd = file_path.endswith((".xsd", ".xml"))
        steps = []
        n = 1

        # 1. Backup
        steps.append(SkillCall(
            skill_name="backup_file",
            arguments={"file_path": file_path},
            reason=f"Backup {file_path} before any modification.",
            step=n,
        ))
        n += 1

        # 2. Read
        steps.append(SkillCall(
            skill_name="read_file",
            arguments={"file_path": file_path},
            reason="Read current file content before generating updates.",
            step=n,
        ))
        n += 1

        # 3. Generate update
        steps.append(SkillCall(
            skill_name="generate_code_update",
            arguments={
                "file_path": file_path,
                "current_content": "__FROM_CONTEXT__",   # executor fills from previous result
                "spec_change": spec_change,
            },
            reason="Generate the updated code via LLM.",
            step=n,
        ))
        n += 1

        # 4. Write
        steps.append(SkillCall(
            skill_name="write_file",
            arguments={
                "file_path": file_path,
                "content": "__FROM_CONTEXT__",
            },
            reason="Write the generated code to disk.",
            step=n,
        ))
        n += 1

        # 5. Verify
        verify_skill = "xml_syntax_check" if is_xsd else "python_syntax_check"
        steps.append(SkillCall(
            skill_name=verify_skill,
            arguments={"file_path": file_path},
            reason="Verify the updated file has no syntax errors.",
            step=n,
        ))
        n += 1

        steps.append(SkillCall(
            skill_name="truncation_check",
            arguments={"file_path": file_path},
            reason="Ensure the LLM did not truncate the file.",
            step=n,
        ))
        n += 1

        if is_xsd:
            steps.append(SkillCall(
                skill_name="xsd_schema_validate",
                arguments={"file_path": file_path},
                reason="Run Phase-1 compatibility probes against updated XSD.",
                step=n,
            ))
            n += 1

        # 6. Run tests
        steps.append(SkillCall(
            skill_name="run_tests",
            arguments={"project_root": project_root},
            reason="Run full automated test suite.",
            step=n,
        ))
        n += 1

        # 7. Hot-reload
        steps.append(SkillCall(
            skill_name="hot_reload",
            arguments={},
            reason="Apply changes to the running server.",
            step=n,
        ))
        n += 1

        # 8. Snapshot + commit
        steps.append(SkillCall(
            skill_name="create_backup_snapshot",
            arguments={
                "project_root": project_root,
                "version": version,
                "description": spec_change[:80],
                "snapshot_type": "post_change",
            },
            reason="Save labeled post-change snapshot.",
            step=n,
        ))
        n += 1

        steps.append(SkillCall(
            skill_name="git_commit",
            arguments={
                "project_root": project_root,
                "message": f"Phase 2 Spec Change v{version}: {spec_change[:80]}",
            },
            reason="Commit changes to git.",
            step=n,
        ))

        return steps
