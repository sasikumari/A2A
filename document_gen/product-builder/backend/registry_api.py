import hashlib
import uuid
import time
from datetime import datetime, timedelta
import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/registry", tags=["Registry"])

# --- In-Memory DB (For Hackathon/Demo) ---
# In a real system, these would safely reside in a hardened DB.
DB_AGENTS = {}  # did -> { org: str, skills: List[str], manifest_hash: str, allowed_callers: List[str], revoked: bool }

# Mock Private/Public key pair for NPCi
# In real life, these would be loaded from an HSM or secure vault.
NPCI_SECRET = "NPCI_SUPER_SECRET_KEY_12345"

# --- Models ---
class RegisterAgentRequest(BaseModel):
    org: str
    skills: List[str]
    allowed_callers: List[str]

class AuthAgentRequest(BaseModel):
    did: str
    org_cert: str

class RefreshTokenRequest(BaseModel):
    did: str
    current_manifest_hash: str

# --- Endpoints ---

@router.post("/register")
def register_agent(req: RegisterAgentRequest):
    """
    Cold path: Register a new agent into the ecosystem.
    Simulates human sign-off and sandbox validation.
    """
    # 1. Generate unique DID
    did = f"did:npci:agent:{uuid.uuid4().hex[:12]}"
    
    # 2. Hash the manifest for integrity checks
    manifest_raw = f"{req.org}:{','.join(req.skills)}:{','.join(req.allowed_callers)}"
    manifest_hash = hashlib.sha256(manifest_raw.encode()).hexdigest()

    # 3. Store in Registry
    DB_AGENTS[did] = {
        "org": req.org,
        "skills": req.skills,
        "manifest_hash": manifest_hash,
        "allowed_callers": req.allowed_callers,
        "revoked": False
    }

    # 返回 signed credential bundle (mock)
    credential_bundle = {
        "did": did,
        "manifest_hash": manifest_hash,
        "issued_at": datetime.utcnow().isoformat()
    }

    return {"status": "success", "bundle": credential_bundle}


@router.post("/auth")
def auth_agent(req: AuthAgentRequest):
    """
    Warm path / Startup: Agent supplies DID + org cert.
    TA does ONE registry lookup and issues a short-lived JWT.
    """
    agent = DB_AGENTS.get(req.did)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent DID not found. Please register first.")
    
    if agent["revoked"]:
        raise HTTPException(status_code=403, detail="Agent is revoked.")
    
    # In a real system, we'd verify the physical `org_cert` signature here.
    # We skip physical cert validation for the demo.
    
    # Issue Short-Lived JWT (15 minutes)
    payload = {
        "agent_id": req.did,
        "org": agent["org"],
        "skills": agent["skills"],
        "allowed_callers": agent["allowed_callers"],
        "manifest_hash": agent["manifest_hash"],
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, NPCI_SECRET, algorithm="HS256")

    return {
        "token": token,
        "expires_in": 900
    }

@router.post("/refresh")
def refresh_token(req: RefreshTokenRequest):
    """
    Warm path / Refresh: Renew token based on manifest_hash if not revoked.
    """
    agent = DB_AGENTS.get(req.did)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent DID not found.")
    
    if agent["revoked"]:
        raise HTTPException(status_code=403, detail="Agent is revoked.")
    
    if agent["manifest_hash"] != req.current_manifest_hash:
        # skill mismatch! This triggers the cold path re-verification requirement.
        raise HTTPException(status_code=400, detail="skill_mismatch: Manifest changed. Please re-register.")
    
    payload = {
        "agent_id": req.did,
        "org": agent["org"],
        "skills": agent["skills"],
        "allowed_callers": agent["allowed_callers"],
        "manifest_hash": agent["manifest_hash"],
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, NPCI_SECRET, algorithm="HS256")

    return {
        "token": token,
        "expires_in": 900
    }
