import json
import threading
import time

class PartyAgent:
    """
    Role: Receive a change manifest, adapt internal systems, run unit tests securely,
    and confirm changes. Operates strictly independently.
    """
    def __init__(self, party_id, party_type, llm_client, notification_bus):
        self.party_id = party_id
        self.party_type = party_type
        self.llm_client = llm_client
        self.bus = notification_bus
        self.current_manifest = None
        
        # Subscribe securely only to topics matching its Party ID context
        self._listener_thread = threading.Thread(target=self._listen, daemon=True)
        self._listener_thread.start()

    def _listen(self):
        """Monitors the bus for spec changes targeting this agent."""
        for event in self.bus.subscribe("spec_change"):
            if event and event.get("party_id") == self.party_id:
                print(f"[PartyAgent:{self.party_id}] Received manifest. Initiating autonomous adaptation.")
                self.current_manifest = event
                self.adapt_system()

    def adapt_system(self):
        """Simulates LLM-driven adaptation + test execution."""
        # 1. Manifest Reader
        changes = self.current_manifest.get("changes", [])
        
        # Simulated LLM logic generating patch files based on the manifest
        system_context = f"You are an autonomous {self.party_type} PartyAgent applying: {changes}"
        # We simulate the file generation here to save actual code destructive modifications
        print(f"[PartyAgent:{self.party_id}] Adapted. Applying {len(changes)} changes inline.")
        
        # 2. Run tests independently using the provided test_vectors
        vectors = []
        for c in changes:
            vectors.extend(c.get("test_vectors", []))
            
        self.test_runner(vectors)

    def test_runner(self, vectors):
        """Runs the validation checks."""
        print(f"[PartyAgent:{self.party_id}] Running {len(vectors)} test vectors locally.")
        time.sleep(1) # simulate testing
        
        # 3. Acknowledgement Sender back to NPCI Orchestrator
        self.acknowledgement_sender(passed=True)
        
    def acknowledgement_sender(self, passed=True):
        """Ships PASS/FAIL validation strictly through the bus back to Phase Gating."""
        # Represents the POST to actual infrastructure "/acknowledge" endpoint
        print(f"[PartyAgent:{self.party_id}] Emitting Ack.")
        self.bus.publish_event("unit_test_ack", {
            "party_id": self.party_id,
            "status": "PASS" if passed else "FAIL",
            "timestamp": time.time()
        })
        
    def manifest_reader(self):
        return self.current_manifest

    def internal_chat(self, msg):
        """Provides internal messaging (human-in-the-loop local org interface)"""
        return f"[PartyAgent:{self.party_id}] Internal Echo: {msg}"
