from switch.notification_bus import NotificationBus
from .llm_client import LLMClient
from .switch_agent import SwitchAgent
from .participant_agents import PayerPSPAgent, PayeePSPAgent, RemitterBankAgent, BeneficiaryBankAgent, ICICIBankAgent
from .reasoning_agent import ReasoningAgent
from .skill_planner import SkillPlanner
from .skills import SkillRegistry, SkillExecutor, SkillCall, SkillResult, Skill
import threading

def init_agents(bus: NotificationBus):
    llm_client = LLMClient()
    reasoning_agent = ReasoningAgent(llm_client)
    
    switch_agent = SwitchAgent(llm_client, bus, reasoning_agent)
    payer_psp_agent = PayerPSPAgent(llm_client, bus)
    payee_psp_agent = PayeePSPAgent(llm_client, bus)
    remitter_bank_agent = RemitterBankAgent(llm_client, bus)
    beneficiary_bank_agent = BeneficiaryBankAgent(llm_client, bus)
    icici_bank_agent = ICICIBankAgent(llm_client, bus)

    # Register files to manage using absolute paths
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def get_abs(rel):
        return os.path.join(project_root, rel)

    switch_agent.register_file(get_abs("switch/upi_switch.py"))
    switch_agent.register_file(get_abs("api/schemas/upi_pay_request.xsd"))
    switch_agent.register_file(get_abs("api/schemas/upi_collect_request.xsd"))
    payer_psp_agent.register_file(get_abs("psps/payer_psp_handler.py"))
    payee_psp_agent.register_file(get_abs("psps/payee_psp_handler.py"))
    remitter_bank_agent.register_file(get_abs("banks/remitter_bank_handler.py"))
    beneficiary_bank_agent.register_file(get_abs("banks/beneficiary_bank_handler.py"))
    icici_bank_agent.register_file(get_abs("banks/icici_bank.py"))
    
    # Use the pre-built universal registry that has all skills correctly wired
    from .skills.registry import get_universal_registry
    skill_registry = get_universal_registry(llm_client)

    # Inject registry into every agent so they can call skills by name
    switch_agent.registry = skill_registry
    payer_psp_agent.registry = skill_registry
    payee_psp_agent.registry = skill_registry
    remitter_bank_agent.registry = skill_registry
    beneficiary_bank_agent.registry = skill_registry
    icici_bank_agent.registry = skill_registry
    
    agents = [switch_agent, payer_psp_agent, payee_psp_agent, remitter_bank_agent, beneficiary_bank_agent, icici_bank_agent]
    
    # Start listening for spec changes
    def spec_change_listener():
        print("[Agents] Listening for spec changes...")
        while True:
            try:
                for event in bus.subscribe("spec_change"):
                    if event:
                        print(f"[Agents] Listener received event: {event}")
                        for agent in agents:
                            if agent != switch_agent: # Switch originates it
                                try:
                                    agent.receive_spec_change(event)
                                except Exception as e:
                                    print(f"[Agents] Error dispatching to {agent.name}: {e}")
            except Exception as e:
                print(f"[Agents] Listener loop error: {e}")
                import time
                time.sleep(1) # Prevent tight loop on persistent error

    threading.Thread(target=spec_change_listener, daemon=True).start()
    
    return switch_agent, agents
