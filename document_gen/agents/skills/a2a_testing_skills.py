"""
A2A Testing Skills — NPCI Ecosystem Verification.
Implements test case pushing and report generation for party sandboxes.
"""

import json
import hashlib
import time
from . import Skill, SkillResult

class PushEcosystemTestsSkill(Skill):
    name = "push_ecosystem_tests"
    description = "Push a set of unit test payloads (XML/JSON) to a participant agent for sandbox verification."
    parameters = {
        "type": "object",
        "properties": {
            "test_cases": {"type": "array", "items": {"type": "object"}, "description": "List of test cases (input payload + expected result)."},
            "txn_type": {"type": "string", "enum": ["PAY", "COLLECT", "MANDATE"]},
            "agent_name": {"type": "string"}
        },
        "required": ["test_cases", "txn_type", "agent_name"]
    }

    def execute(self, test_cases: list, txn_type: str, agent_name: str, **_) -> SkillResult:
        try:
            payload = {
                "type": "TEST_PUSH_INTENT",
                "txn_type": txn_type,
                "test_cases": test_cases,
                "pushed_ts": time.time()
            }
            # The actual "push" happens via the SwitchAgent bus publish.
            # This skill formats the test package.
            return SkillResult(success=True, output=json.dumps(payload), metadata={"agent": agent_name})
        except Exception as e:
            return SkillResult(success=False, error=str(e))

class GenerateTestReportSkill(Skill):
    name = "generate_test_report"
    description = "Generate a formal PASS/FAIL report for NPCI after running pushed test cases in the sandbox."
    parameters = {
        "type": "object",
        "properties": {
            "test_results": {"type": "array", "items": {"type": "object"}, "description": "Detailed local test execution results."},
            "agent_name": {"type": "string"}
        },
        "required": ["test_results", "agent_name"]
    }

    def execute(self, test_results: list, agent_name: str, **_) -> SkillResult:
        try:
            total = len(test_results)
            passed = sum(1 for r in test_results if r.get("status") == "PASS")
            failed_scenarios = [r.get("scenario") for r in test_results if r.get("status") != "PASS"]
            
            report = {
                "type": "TEST_REPORT_ACK",
                "agent": agent_name,
                "summary": "PASS" if total == passed else "FAIL",
                "stats": f"{passed}/{total} passed",
                "deviation": ", ".join(failed_scenarios) if failed_scenarios else "None",
                "report_ts": time.time()
            }
            # NPCI should only see this summary report, not the internal code/state.
            return SkillResult(success=True, output=json.dumps(report))
        except Exception as e:
            return SkillResult(success=False, error=str(e))
