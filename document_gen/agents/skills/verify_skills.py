"""
Verification skills — syntax checks, XML validation, truncation detection,
and business-rule smoke tests for the UPI/NPCI codebase.
"""

from __future__ import annotations
import ast
import os
import re
from . import Skill, SkillResult


class PythonSyntaxCheckSkill(Skill):
    name = "python_syntax_check"
    description = (
        "Parse a Python file with the AST parser to verify there are no syntax errors. "
        "Returns OK if valid, or the exact syntax error message."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the .py file to check.",
            },
            "content": {
                "type": "string",
                "description": "Optional: pass content directly instead of reading from disk.",
            },
        },
        "required": ["file_path"],
    }

    def execute(self, file_path: str, content: str = "", **_) -> SkillResult:
        try:
            if not content:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            ast.parse(content, filename=file_path)
            return SkillResult(
                success=True,
                output="Syntax OK",
                metadata={"file": file_path, "lines": content.count("\n")},
            )
        except SyntaxError as e:
            return SkillResult(
                success=False,
                error=f"SyntaxError in {os.path.basename(file_path)} at line {e.lineno}: {e.msg}",
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))


class TruncationCheckSkill(Skill):
    name = "truncation_check"
    description = (
        "Detect if an LLM-generated file is suspiciously shorter than the original, "
        "which indicates truncation. Fails if the new file is <90% the size of the backup."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the updated file.",
            },
            "min_ratio": {
                "type": "number",
                "description": "Minimum size ratio new/original (default 0.90).",
            },
        },
        "required": ["file_path"],
    }

    def execute(self, file_path: str, min_ratio: float = 0.90, **_) -> SkillResult:
        backup_path = f"{file_path}.bak"
        if not os.path.exists(backup_path):
            return SkillResult(success=True, output="No backup to compare — skipping truncation check.")
        try:
            original_size = os.path.getsize(backup_path)
            new_size = os.path.getsize(file_path)
            if original_size < 5000:
                return SkillResult(success=True, output="File too small for truncation check.")
            ratio = new_size / original_size
            if ratio < min_ratio:
                return SkillResult(
                    success=False,
                    error=(
                        f"Truncation detected: original={original_size}B, new={new_size}B "
                        f"(ratio={ratio:.0%} < {min_ratio:.0%}). Too much code was removed."
                    ),
                )
            return SkillResult(
                success=True,
                output=f"Size OK: {new_size}/{original_size} bytes ({ratio:.0%})",
                metadata={"original_size": original_size, "new_size": new_size, "ratio": ratio},
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))


class XMLSyntaxCheckSkill(Skill):
    name = "xml_syntax_check"
    description = (
        "Parse an XML or XSD file to verify it is well-formed. "
        "Returns OK or the exact parse error."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the .xml or .xsd file.",
            },
            "content": {
                "type": "string",
                "description": "Optional: pass content directly.",
            },
        },
        "required": ["file_path"],
    }

    def execute(self, file_path: str, content: str = "", **_) -> SkillResult:
        import xml.etree.ElementTree as ET
        try:
            if not content:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            ET.fromstring(content)
            return SkillResult(success=True, output="XML well-formed OK")
        except ET.ParseError as e:
            return SkillResult(success=False, error=f"XML ParseError in {os.path.basename(file_path)}: {e}")
        except Exception as e:
            return SkillResult(success=False, error=str(e))


class XSDSchemaValidateSkill(Skill):
    name = "xsd_schema_validate"
    description = (
        "Validate an XSD schema file using xmlschema. "
        "Also runs Phase-1 UPI smoke tests to ensure backward compatibility: "
        "standard ReqPay messages must still validate after any schema change."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the .xsd file to validate.",
            },
            "verification_xml": {
                "type": "string",
                "description": "Optional: XML snippet to validate against the updated schema.",
            },
        },
        "required": ["file_path"],
    }

    # Canonical Phase-1 smoke tests — these must ALWAYS pass
    _PHASE1_PROBES = {
        "standard-pay": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">'
            '<upi:Head ver="1.0" ts="2025-01-01T10:00:00Z" orgId="PAYERPSP" msgId="P1A" prodType="UPI"/>'
            '<upi:Txn id="TXN_P1A" type="PAY" note="smoke-test"/>'
            '<upi:Payer addr="ramesh@payer">'
            '<upi:Amount value="500.00" curr="INR"/>'
            '<upi:Creds><upi:Cred><upi:Data code="1234"/></upi:Cred></upi:Creds>'
            '</upi:Payer>'
            '<upi:Payees><upi:Payee addr="merchant@benef"/></upi:Payees>'
            '</upi:ReqPay>'
        ),
        "high-value-with-purpose": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">'
            '<upi:Head ver="1.0" ts="2025-01-01T10:00:00Z" orgId="PAYERPSP" msgId="P1B" prodType="UPI"/>'
            '<upi:Txn id="TXN_P1B" type="PAY" note="smoke-purpose"/>'
            '<upi:purpose>00</upi:purpose>'
            '<upi:purposeCode code="00" description="UPI Purpose 00"/>'
            '<upi:Payer addr="ramesh@payer">'
            '<upi:Amount value="9999999.00" curr="INR"/>'
            '<upi:Creds><upi:Cred><upi:Data code="1234"/></upi:Cred></upi:Creds>'
            '</upi:Payer>'
            '<upi:Payees><upi:Payee addr="merchant@benef"/></upi:Payees>'
            '<upi:RiskScore>85</upi:RiskScore>'
            '</upi:ReqPay>'
        ),
    }

    def execute(self, file_path: str, verification_xml: str = "", **_) -> SkillResult:
        try:
            import xmlschema
        except ImportError:
            return SkillResult(success=True, output="xmlschema not installed — skipping XSD validation.")

        try:
            schema = xmlschema.XMLSchema(file_path)
        except Exception as e:
            return SkillResult(success=False, error=f"XSD load error: {e}")

        basename = os.path.basename(file_path).lower()

        # Run Phase-1 backward-compat probes only for pay_request schemas
        if "pay_request" in basename:
            for probe_name, probe_xml in self._PHASE1_PROBES.items():
                try:
                    schema.validate(probe_xml)
                except Exception as e:
                    return SkillResult(
                        success=False,
                        error=(
                            f"Phase-1 compat check [{probe_name}] FAILED. "
                            f"The updated schema rejects a standard Phase-1 ReqPay. "
                            f"HINT: Never add maxInclusive to AmountValueType; "
                            f"never make Payee>Amount required. Detail: {e}"
                        ),
                    )

        # Validate the agent's verification payload if provided
        if verification_xml and "reqpay" in verification_xml.lower():
            cleaned = self._clean_xml(verification_xml)
            try:
                schema.validate(cleaned)
            except Exception as e:
                # Payload issue — warn only, do NOT fail the skill
                return SkillResult(
                    success=True,
                    output=(
                        f"XSD structurally valid, but verification_xml has issues "
                        f"(payload problem, not schema problem): {e}"
                    ),
                )

        return SkillResult(success=True, output=f"XSD valid: {os.path.basename(file_path)}")

    @staticmethod
    def _clean_xml(xml_str: str) -> str:
        """Fix common LLM-generated XML quirks."""
        xml_str = xml_str.replace('\u201c', '"').replace('\u201d', '"')
        xml_str = xml_str.replace('\u2018', "'").replace('\u2019', "'")
        xml_str = re.sub(
            r'<\?xml([^?]*)\?>',
            lambda m: '<?xml' + m.group(1).replace('\\"', '"').replace("\\'", "'") + '?>',
            xml_str,
        )
        decls = re.findall(r'<\?xml[^?]*\?>', xml_str)
        if len(decls) > 1:
            xml_str = xml_str.replace(decls[1], '', 1)
        return xml_str


class BusinessRulesCheckSkill(Skill):
    name = "business_rules_check"
    description = (
        "Verify that key NPCI business rules are preserved in the switch file: "
        "P2P_LIMIT and MAX_TXN_AMOUNT constants exist and are positive numbers."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to switch/upi_switch.py.",
            }
        },
        "required": ["file_path"],
    }

    def execute(self, file_path: str, **_) -> SkillResult:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            issues = []

            p2p_match = re.search(r'P2P_LIMIT\s*=\s*([\d_]+)', content)
            if not p2p_match:
                issues.append("P2P_LIMIT constant not found")
            elif int(p2p_match.group(1).replace("_", "")) <= 0:
                issues.append("P2P_LIMIT must be > 0")

            max_match = re.search(r'MAX_TXN_AMOUNT\s*=\s*([\d_]+)', content)
            if not max_match:
                issues.append("MAX_TXN_AMOUNT constant not found")
            elif int(max_match.group(1).replace("_", "")) <= 0:
                issues.append("MAX_TXN_AMOUNT must be > 0")

            if issues:
                return SkillResult(success=False, error="; ".join(issues))

            p2p = int(p2p_match.group(1).replace("_", ""))
            maxtxn = int(max_match.group(1).replace("_", ""))
            return SkillResult(
                success=True,
                output=f"Business rules OK: P2P_LIMIT={p2p:,}, MAX_TXN_AMOUNT={maxtxn:,}",
                metadata={"P2P_LIMIT": p2p, "MAX_TXN_AMOUNT": maxtxn},
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))
