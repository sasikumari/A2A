"""
A2A Handshake Skills — NPCI Titanium Standard.
Implements Change Manifest generation, PKI signing, and Acknowledgment.
"""

import json
import hashlib
import hmac
import time
from . import Skill, SkillResult

class SignManifestSkill(Skill):
    name = "sign_manifest"
    description = "Sign a Change Manifest JSON using NPCI PKI (simulated with HMAC) for A2A integrity."
    parameters = {
        "type": "object",
        "properties": {
            "manifest_json": {"type": "string", "description": "The JSON manifest to sign."},
            "secret_key": {"type": "string", "description": "NPCI shared secret key for signing."}
        },
        "required": ["manifest_json", "secret_key"]
    }

    def execute(self, manifest_json: str, secret_key: str, **_) -> SkillResult:
        try:
            # Normalize the JSON to ensure deterministic hashing
            normalized_manifest = json.dumps(json.loads(manifest_json), separators=(',', ':'))
            
            # Simulated signing: HMAC-SHA256
            signature = hmac.new(
                secret_key.encode(),
                normalized_manifest.encode(),
                hashlib.sha256
            ).hexdigest()
            
            signed_payload = {
                "manifest": json.loads(normalized_manifest),
                "signature": signature,
                "signer": "NPCI_ORCHESTRATOR",
                "ts": time.time()
            }
            return SkillResult(success=True, output=json.dumps(signed_payload))
        except Exception as e:
            return SkillResult(success=False, error=str(e))

class VerifySignatureSkill(Skill):
    name = "verify_signature"
    description = "Verify the NPCI signature on an incoming Change Manifest or ACK."
    parameters = {
        "type": "object",
        "properties": {
            "signed_payload": {"type": "string", "description": "The full signed payload JSON."},
            "secret_key": {"type": "string", "description": "Shared secret key for verification."}
        },
        "required": ["signed_payload", "secret_key"]
    }

    def execute(self, signed_payload: str, secret_key: str, **_) -> SkillResult:
        try:
            data = json.loads(signed_payload)
            manifest = data.get("manifest")
            signature = data.get("signature")
            
            if not manifest or not signature:
                return SkillResult(success=False, error="Invalid signed payload format.")
                
            # Re-calculate signature
            normalized_manifest = json.dumps(manifest, separators=(',', ':'))
            expected = hmac.new(
                secret_key.encode(),
                normalized_manifest.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if hmac.compare_digest(expected, signature):
                return SkillResult(success=True, output="VERIFIED")
            else:
                return SkillResult(success=False, error="Signature mismatch — Integrity compromised.")
        except Exception as e:
            return SkillResult(success=False, error=str(e))

class GenerateManifestSkill(Skill):
    name = "generate_manifest"
    description = "Generate a per-party Change Manifest from a master Technical Specification Document (TSD)."
    parameters = {
        "type": "object",
        "properties": {
            "tsd": {"type": "string", "description": "Master Technical Specification Document."},
            "target_party": {"type": "string", "enum": ["PAYER_PSP", "PAYEE_PSP", "REMITTER_BANK", "BENEFICIARY_BANK"]},
            "feature_name": {"type": "string"}
        },
        "required": ["tsd", "target_party", "feature_name"]
    }

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def execute(self, tsd: str, target_party: str, feature_name: str, **_) -> SkillResult:
        system = f"You are the NPCI Change Management Engine. Generate a per-party Change Manifest for {target_party}."
        prompt = f"""Based on the following TSD for '{feature_name}', create a constrained JSON manifest for {target_party}.
        
TSD:
{tsd}

The manifest MUST follow this structure:
{{
  "feature": "{feature_name}",
  "party": "{target_party}",
  "api_changes": [ ... list of specific field adds/changes ... ],
  "contract_updates": [ ... timeout rules, retry limits ... ],
  "error_codes": {{ ... new codes to handle ... }},
  "instruction_dsl": "Describe implementation plan in 2-3 sentences"
}}

Return ONLY valid JSON.
"""
        try:
            response = self.llm_client.query(prompt, system=system)
            # Find JSON block
            import re
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                return SkillResult(success=True, output=match.group())
            return SkillResult(success=False, error="LLM did not return valid JSON manifest.")
        except Exception as e:
            return SkillResult(success=False, error=str(e))

class AcknowledgeIntentSkill(Skill):
    name = "acknowledge_intent"
    description = "Generate a signed Acknowledgment for a received Change Manifest."
    parameters = {
        "type": "object",
        "properties": {
            "manifest_hash": {"type": "string", "description": "Hash of the accepted manifest."},
            "agent_name": {"type": "string"},
            "secret_key": {"type": "string"}
        },
        "required": ["manifest_hash", "agent_name", "secret_key"]
    }

    def execute(self, manifest_hash: str, agent_name: str, secret_key: str, **_) -> SkillResult:
        try:
            ack_msg = {
                "status": "ACCEPTED",
                "manifest_hash": manifest_hash,
                "agent": agent_name,
                "ack_ts": time.time()
            }
            ack_json = json.dumps(ack_msg, separators=(',', ':'))
            signature = hmac.new(
                secret_key.encode(),
                ack_json.encode(),
                hashlib.sha256
            ).hexdigest()
            
            signed_ack = {
                "manifest": ack_msg,
                "signature": signature,
                "signer": agent_name
            }
            return SkillResult(success=True, output=json.dumps(signed_ack))
        except Exception as e:
            return SkillResult(success=False, error=str(e))
