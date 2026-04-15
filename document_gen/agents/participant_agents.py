from .base_agent import BaseAgent

class PayerPSPAgent(BaseAgent):
    def __init__(self, llm_client, bus):
        super().__init__("PayerPSPAgent", "PAYER_PSP", llm_client, bus)

    def _extra_skills(self):
        from .skills.transactional_skills import VerifyVpaSkill
        return [VerifyVpaSkill()]

class PayeePSPAgent(BaseAgent):
    def __init__(self, llm_client, bus):
        super().__init__("PayeePSPAgent", "PAYEE_PSP", llm_client, bus)

    def _extra_skills(self):
        from .skills.transactional_skills import VerifyVpaSkill
        return [VerifyVpaSkill()]

class RemitterBankAgent(BaseAgent):
    def __init__(self, llm_client, bus):
        super().__init__("RemitterBankAgent", "REMITTER_BANK", llm_client, bus)

    def _extra_skills(self):
        from .skills.transactional_skills import ProcessPostingSkill
        return [ProcessPostingSkill()]

class BeneficiaryBankAgent(BaseAgent):
    def __init__(self, llm_client, bus):
        super().__init__("BeneficiaryBankAgent", "BENEFICIARY_BANK", llm_client, bus)

    def _extra_skills(self):
        from .skills.transactional_skills import ProcessPostingSkill
        return [ProcessPostingSkill()]

class ICICIBankAgent(BaseAgent):
    def __init__(self, llm_client, bus):
        super().__init__("ICICIBankAgent", "ICICIBANK", llm_client, bus)
    
    def _extra_skills(self):
        from .skills.transactional_skills import ProcessPostingSkill
        return [ProcessPostingSkill()]
