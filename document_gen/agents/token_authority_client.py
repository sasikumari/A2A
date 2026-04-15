import time
import requests
import jwt
from datetime import datetime

REGISTRY_URL = "http://localhost:8001/api/registry"
NPCI_PUBLIC_KEY = "NPCI_SUPER_SECRET_KEY_12345" # In reality, parsed from X.509 cert

class AgentSession:
    def __init__(self, did: str, token: str, manifest_hash: str):
        self.did = did
        self.current_token = token
        self.manifest_hash = manifest_hash

class TokenAuthorityClient:
    """
    Client SDK to talk to the Token Authority.
    Handles startup authentication, automatic token refresh, and offline JWT verification.
    """
    def __init__(self, org_name: str, agent_name: str):
        self.org_name = org_name
        self.agent_name = agent_name
        self.session = None

    def auto_register_and_auth(self, skills: list, allowed_callers: list) -> AgentSession:
        """
        Demo Helper: Registers the agent automatically to get a DID, then authenticates.
        In production, registration is a completely separate offline human process.
        """
        # 1. Register (Cold Path)
        reg_payload = {
            "org": self.org_name,
            "skills": skills,
            "allowed_callers": allowed_callers
        }
        res = requests.post(f"{REGISTRY_URL}/register", json=reg_payload)
        
        if res.status_code != 200:
            print(f"[TA] Auto-register failed: {res.text}")
            return None
        
        bundle = res.json().get("bundle", {})
        did = bundle.get("did")
        manifest_hash = bundle.get("manifest_hash")

        # 2. Authenticate (Warm Path Startup)
        auth_payload = {
            "did": did,
            "org_cert": "MOCK_CERT_VALID"
        }
        auth_res = requests.post(f"{REGISTRY_URL}/auth", json=auth_payload)
        
        if auth_res.status_code != 200:
            print(f"[TA] Auth failed: {auth_res.text}")
            return None

        token = auth_res.json().get("token")
        self.session = AgentSession(did, token, manifest_hash)
        print(f"[{self.agent_name}] Obtained A2A Session Token (DID: {did})")
        return self.session

    def refresh_token(self):
        """
        Lightweight revocation and manifest hash check to renew JWT.
        """
        if not self.session:
            return

        payload = {
            "did": self.session.did,
            "current_manifest_hash": self.session.manifest_hash
        }
        res = requests.post(f"{REGISTRY_URL}/refresh", json=payload)
        if res.status_code == 200:
            self.session.current_token = res.json().get("token")
            # print(f"[{self.agent_name}] Token Refreshed.")
        else:
            print(f"[{self.agent_name}] 🔴 Token Refresh Failed! {res.text}")
            self.session = None

    def verify_remote_jwt(self, token: str) -> dict:
        """
        Very fast offline verification of an incoming A2A message JWT.
        No network call required. Trust is derived from the cryptographic signature.
        """
        try:
            decoded = jwt.decode(token, NPCI_PUBLIC_KEY, algorithms=["HS256"])
            # Return claims
            return decoded
        except jwt.ExpiredSignatureError:
            print(f"[{self.agent_name}] 🛑 Rejecting A2A Message: JWT Expired.")
            return None
        except jwt.InvalidTokenError as e:
            print(f"[{self.agent_name}] 🛑 Rejecting A2A Message: Invalid JWT ({str(e)}).")
            return None

token_authority = TokenAuthorityClient("NPCI", "DefaultAgent")
