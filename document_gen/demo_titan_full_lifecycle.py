"""
Titan-III Full 8-Phase A2A Orchestration Demo.
Simulates the entire NPCI lifecycle: Idea -> 8 Phases -> A2A Manifest -> ACK -> Test -> Deploy.
"""

import threading
import time
import json
from agents.switch_agent import SwitchAgent
from agents.participant_agents import PayerPSPAgent, PayeePSPAgent, RemitterBankAgent, BeneficiaryBankAgent
from agents.llm_client import LLMClient

class MockBus:
    """Simulated event bus for the demo."""
    def __init__(self):
        self.listeners = {}

    def publish_event(self, topic, event):
        if topic not in self.listeners:
            self.listeners[topic] = []
        # In a real bus, this would be an async dispatch. 
        # Here we just keep it simple for the script.
        for callback in self.listeners[topic]:
            callback(event)

    def subscribe(self, topic):
        """Returns a generator for events on a topic."""
        q = []
        def listener(ev):
            q.append(ev)
        
        if topic not in self.listeners:
            self.listeners[topic] = []
        self.listeners[topic].append(listener)
        
        while True:
            if q:
                yield q.pop(0)
            time.sleep(0.1)

def run_demo():
    bus = MockBus()
    llm = LLMClient()
    
    print("--- 1. INITIALIZING TITAN ECOSYSTEM ---")
    switch = SwitchAgent(llm, bus)
    payer = PayerPSPAgent(llm, bus)
    payee = PayeePSPAgent(llm, bus)
    remitter = RemitterBankAgent(llm, bus)
    beneficiary = BeneficiaryBankAgent(llm, bus)
    
    # Start Agent Listeners in background threads
    print(f"[{switch.name}] 🚀 Starting background A2A listeners for all parties...")
    for agent in [payer, payee, remitter, beneficiary]:
        threading.Thread(target=agent._start_auth_listener, daemon=True).start()
    
    # Give them a moment to initialize
    time.sleep(1)
    
    def auto_approver():
        """Simulates the NPCI Human Auditor approving each phase."""
        time.sleep(1)
        sub = bus.subscribe("agent_status")
        for event in sub:
            if event.get("status") == "AWAITING_APPROVAL":
                phase = event.get("phase")
                print(f"\n[AUDITOR] Reviewing {phase}... [APPROVING]")
                time.sleep(0.5)
                bus.publish_event("human_approval", {"phase": phase, "decision": "APPROVE"})
                if phase == "FINAL_DEPLOYMENT":
                    break

    threading.Thread(target=auto_approver, daemon=True).start()

    print("\n--- 2. PRODUCT MANAGER TRIGGER ---")
    prompt = "Add a new 'IoT-Device' purpose code (category 1092) for high-velocity smart-meter payments."
    
    # Step 1: Switch analyzes and plans
    # (Simulating successful reasoning_agent call)
    plan = {
        "version": "2.1.0",
        "feature_name": "IoT Smart Payments",
        "tsd": "NP-2026-IOT: New Purpose Code 1092. Latency max 2s. MFA required.",
        "brd": "Business Requirement for automated smart meter utilities."
    }

    print("\n--- 3. STARTING 8-PHASE ORCHESTRATION ---")
    success = switch.execute_spec_change(plan)
    
    if success:
        print("\n--- 4. ORCHESTRATION COMPLETE ---")
        print("Ecosystem v2.1.0 is now LIVE and SYNCED across all agents.")
    else:
        print("\n--- 4. ORCHESTRATION FAILED ---")

if __name__ == "__main__":
    run_demo()
