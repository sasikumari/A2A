"""
Transactional Domain Skills — UPI Real-World Execution.
Implements VPA verification, account posting, and routing logic for Switch/Banks/PSPs.
"""

from . import Skill, SkillResult
import datetime

class VerifyVpaSkill(Skill):
    name = "verify_vpa"
    description = "Verify a Payer or Payee VPA and retrieve beneficiary name/details from the PSP registry."
    parameters = {
        "type": "object",
        "properties": {
            "vpa": {"type": "string"},
            "role": {"type": "string", "enum": ["PAYER", "PAYEE"]}
        },
        "required": ["vpa", "role"]
    }

    def execute(self, vpa: str, role: str, **kwargs) -> SkillResult:
        # In a real system, this would query the PSP's local DB or a central directory.
        if "@" not in vpa:
            return SkillResult(success=False, error=f"Invalid VPA format: {vpa}")
        
        # Simulated success
        name = f"Titan {role.capitalize()} {vpa.split('@')[0]}"
        return SkillResult(
            success=True, 
            output={"vpa": vpa, "name": name, "status": "VERIFIED"},
            metadata={"role": role}
        )

class ProcessPostingSkill(Skill):
    name = "process_posting"
    description = "Execute a formal debit or credit posting against the Core Banking System (CBS)."
    parameters = {
        "type": "object",
        "properties": {
            "vpa": {"type": "string"},
            "amount": {"type": "number"},
            "type": {"type": "string", "enum": ["DEBIT", "CREDIT"]},
            "txn_id": {"type": "string"}
        },
        "required": ["vpa", "amount", "type", "txn_id"]
    }

    def execute(self, vpa: str, amount: float, type: str, txn_id: str, **kwargs) -> SkillResult:
        # Resolve CBS from context (passed by the executing Agent)
        context = kwargs.get("_context", {})
        cbs = context.get("cbs")
        
        if not cbs:
             return SkillResult(success=False, error="Critical: CBS interface not found in execution context.")
        
        try:
            acc = cbs.get_account_by_vpa(vpa)
            if type == "DEBIT":
                utr = cbs.debit(acc.id, amount)
            else:
                utr = cbs.credit(acc.id, amount)
                
            return SkillResult(
                success=True, 
                output={"utr": utr, "status": "COMPLETED", "ts": datetime.datetime.utcnow().isoformat()},
                metadata={"vpa": vpa, "type": type}
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))

class RouteToPartySkill(Skill):
    name = "route_to_party"
    description = "NPCI Switch skill to route a payload (Manifest, ReqPay, or Test) to a specific party on the A2A bus."
    parameters = {
        "type": "object",
        "properties": {
            "target_party": {"type": "string"},
            "payload": {"type": "string", "description": "JSON string of the payload to route."},
            "type": {"type": "string", "enum": ["MANIFEST", "REQPAY", "TEST_PUSH"]}
        },
        "required": ["target_party", "payload", "type"]
    }

    def execute(self, target_party: str, payload: str, type: str, **kwargs) -> SkillResult:
        bus = kwargs.get("_context", {}).get("bus")
        if not bus:
            return SkillResult(success=False, error="Bus interface not found in context.")
        
        # Route to a party-specific sub-topic
        topic = f"a2a.{target_party}.{type.lower()}"
        bus.publish_event(topic, {"sender": "NPCI_SWITCH", "content": payload})
        
        return SkillResult(success=True, output=f"Routed {type} to {target_party} on topic {topic}")
