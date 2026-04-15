"""
Code intelligence skills — LLM-powered code generation, impact analysis,
codebase search, and change explanation.
"""

from __future__ import annotations
import os
import re
from . import Skill, SkillResult


class GenerateCodeUpdateSkill(Skill):
    name = "generate_code_update"
    description = (
        "Use the LLM to generate updated code for a file given a spec-change description. "
        "Returns the full updated file content. "
        "Respects NPCI/UPI technical standards automatically."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file being updated.",
            },
            "current_content": {
                "type": "string",
                "description": "Current file content (read via read_file first).",
            },
            "spec_change": {
                "type": "string",
                "description": "Human-readable description of what needs to change.",
            },
            "error_context": {
                "type": "string",
                "description": "Optional: error from a previous failed attempt to fix.",
            },
            "prefer_patch": {
                "type": "boolean",
                "description": "If true, ask for SEARCH/REPLACE patch instead of full file.",
            },
        },
        "required": ["file_path", "current_content", "spec_change"],
    }

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def execute(
        self,
        file_path: str,
        current_content: str,
        spec_change: str,
        brd: str = "",
        tsd: str = "",
        error_context: str = "",
        prefer_patch: bool = False,
        **_,
    ) -> SkillResult:
        file_type = "xml" if file_path.endswith((".xsd", ".xml")) else "python"
        force_full = bool(error_context and (
            "Failed to match SEARCH block" in error_context
            or "Truncation detected" in error_context
        ))

        result = self.llm_client.generate_code_update(
            spec_change_description=spec_change,
            current_code=current_content,
            file_path=file_path,
            file_type=file_type,
            brd=brd,
            tsd=tsd,
            error_context=error_context or None,
            force_full_file=force_full,
        )

        if result is None:
            return SkillResult(
                success=False,
                error="LLM returned no content after retries.",
            )

        return SkillResult(
            success=True,
            output=result,
            metadata={
                "file": file_path,
                "is_patch": "<<<< SEARCH" in result,
                "output_length": len(result),
            },
        )


class AnalyzeImpactSkill(Skill):
    name = "analyze_impact"
    description = (
        "Analyze a spec-change request and produce a structured impact plan: "
        "which files to modify, what changes are needed, risk level, "
        "and a verification XML payload. Returns JSON."
    )
    parameters = {
        "type": "object",
        "properties": {
            "request": {
                "type": "string",
                "description": "The PM or OC change request in plain English.",
            },
            "file_map": {
                "type": "object",
                "description": (
                    "Optional map of logical component → file paths "
                    "(e.g. {\"switch\": [\"switch/upi_switch.py\"]})."
                ),
            },
        },
        "required": ["request"],
    }

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def execute(self, request: str, file_map: dict = None, **_) -> SkillResult:
        import json
        file_map_text = ""
        if file_map:
            file_map_text = "\n".join(
                f"  {comp}: {', '.join(paths)}"
                for comp, paths in file_map.items()
            )

        prompt = f"""You are a Senior NPCI Senior Product Steering Committee Member and Lead Technical Architect.
Analyze this specification change (PM/OC request) and produce a high-fidelity TITANIUM change plan.

REQUEST: {request}

NPCI TITANIUM STANDARDS:
1. EXTREMELY FORMAL: Use official NPCI regulatory tone.
2. UNIVERSAL 11-POINT CANONICAL: In compliance_notes, always align with the NPCI 11-point structure.
3. TECHNICAL RIGOR: Provide specific XML fields and detailed change descriptions.
4. BRANDING: Mark plan as 'NPCI | CONFIDENTIAL'.

FILE MAP (Reference for component ownership):
{file_map_text or "  switch/upi_switch.py (limits, routing, risk logic)"}
  psps/payer_psp.py, psps/payer_psp_handler.py (auth, PIN, initiator)
  psps/payee_psp.py, psps/payee_psp_handler.py (payee credit)
  banks/remitter_bank.py, banks/remitter_bank_handler.py (debit, balance)
  banks/beneficiary_bank.py (beneficiary credit)
  api/schemas/upi_pay_request.xsd (XML structure, optional fields only)

CRITICAL RULES:
1. Limit changes (P2P/max amount) → ONLY switch/upi_switch.py. Never touch the XSD.
2. NEVER add maxInclusive/minInclusive to AmountValueType in XSD.
3. NEVER make Payee>Amount required in XSD (must stay minOccurs=0).
4. Preserve xs:sequence order in XSD.

Return ONLY valid JSON (no markdown):
{{
  "version": "1.x",
  "description": "Formal NPCI Product Header",
  "files_to_change": ["list of file paths that need changes"],
  "change_plan": ["1. Change in file X: [Specific Technical Detail]", "2. Change in file Y: [Specific Technical Detail]"],
  "risk_level": "High|Medium|Low",
  "risk_reason": "Formal risk assessment following NPCI Risk Framework",
  "compliance_notes": "11-Point Canonical Summary: [Summary for each of the 11 points]",
  "verification_payload": "<?xml ...Complete valid ReqPay XML following NPCI technical standards...>",
  "change_manifest": {{
    "intent_blocks": [
      {{
        "target_agent": "SwitchAgent|PayerAgent|PayeeAgent|BankAgent",
        "intent": "Formal functional change intent",
        "context": "Regulatory/Business alignment context",
        "files_to_change": ["affected/files.py"]
      }}
    ]
  }}
}}"""

        raw = self.llm_client.query(prompt)
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        try:
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1:
                plan = json.loads(raw[start:end + 1])
            else:
                plan = json.loads(raw)
            return SkillResult(success=True, output=plan)
        except Exception as e:
            return SkillResult(
                success=False,
                error=f"Could not parse impact analysis JSON: {e}. Raw: {raw[:300]}",
            )


class SearchCodebaseSkill(Skill):
    name = "search_codebase"
    description = (
        "Search all Python/XSD files in the project for a keyword or regex. "
        "Returns a list of {file, line_number, line} matches. "
        "Use to understand where a constant, function, or XML element is defined."
    )
    parameters = {
        "type": "object",
        "properties": {
            "root_dir": {
                "type": "string",
                "description": "Root directory to search from.",
            },
            "pattern": {
                "type": "string",
                "description": "Python regex or plain keyword to search for.",
            },
            "file_extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Extensions to search (default: [\".py\", \".xsd\", \".xml\"]).",
            },
        },
        "required": ["root_dir", "pattern"],
    }

    def execute(
        self,
        root_dir: str,
        pattern: str,
        file_extensions: list = None,
        **_,
    ) -> SkillResult:
        exts = tuple(file_extensions or [".py", ".xsd", ".xml"])
        matches = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return SkillResult(success=False, error=f"Invalid regex: {e}")

        try:
            for dirpath, _, filenames in os.walk(root_dir):
                # Skip venv / .git / __pycache__
                if any(skip in dirpath for skip in [".git", "__pycache__", "venv", ".venv", "node_modules"]):
                    continue
                for fname in filenames:
                    if fname.endswith(exts):
                        fpath = os.path.join(dirpath, fname)
                        try:
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                for i, line in enumerate(f, 1):
                                    if regex.search(line):
                                        matches.append({
                                            "file": fpath,
                                            "line": i,
                                            "content": line.strip(),
                                        })
                        except Exception:
                            continue
        except Exception as e:
            return SkillResult(success=False, error=str(e))

        return SkillResult(
            success=True,
            output=matches,
            metadata={"pattern": pattern, "match_count": len(matches)},
        )


class ExplainChangeSkill(Skill):
    name = "explain_change"
    description = (
        "Produce a human-readable summary of what changed between the original "
        "and updated file content. Highlights added/removed lines and the intent."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "File that was changed.",
            },
            "original": {
                "type": "string",
                "description": "Original file content.",
            },
            "updated": {
                "type": "string",
                "description": "Updated file content.",
            },
        },
        "required": ["file_path", "original", "updated"],
    }

    def execute(self, file_path: str, original: str, updated: str, **_) -> SkillResult:
        import difflib
        orig_lines = original.splitlines(keepends=True)
        upd_lines = updated.splitlines(keepends=True)
        diff = list(difflib.unified_diff(
            orig_lines, upd_lines,
            fromfile=f"original/{os.path.basename(file_path)}",
            tofile=f"updated/{os.path.basename(file_path)}",
            n=2,
        ))
        added = sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))
        removed = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))
        summary = (
            f"{os.path.basename(file_path)}: +{added} lines, -{removed} lines\n"
            + "".join(diff[:60])
            + ("... (truncated)" if len(diff) > 60 else "")
        )
        return SkillResult(
            success=True,
            output=summary,
            metadata={"added": added, "removed": removed, "diff_lines": len(diff)},
        )
