"""
Universal NPCI Skill Registry — Central mapping for the 11-stage Agentic Lifecycle.
"""

from . import SkillRegistry
from .spec_skills import GenerateCanonicalSpecSkill, FormalizeBRDSkill, SyncIntentSkill
from .clarify_skills import ClarifyIntentSkill
from .cert_skills import CertifyPillarSkill
from .kit_skills import GenerateProductKitSkill
from .handshake_skills import SignManifestSkill, VerifySignatureSkill, GenerateManifestSkill, AcknowledgeIntentSkill
from .a2a_testing_skills import PushEcosystemTestsSkill, GenerateTestReportSkill
from .transactional_skills import VerifyVpaSkill, ProcessPostingSkill, RouteToPartySkill

def get_universal_registry(llm_client) -> SkillRegistry:
    registry = SkillRegistry()
    
    # 1. Clarification & Concept Skills
    registry.register(ClarifyIntentSkill(llm_client))
    
    # 2. Canvas, Spec & BRD Skills
    registry.register(GenerateCanonicalSpecSkill(llm_client))
    registry.register(FormalizeBRDSkill(llm_client))
    registry.register(SyncIntentSkill(llm_client))
    
    # 3. A2A Handshake Skills
    registry.register(SignManifestSkill())
    registry.register(VerifySignatureSkill())
    registry.register(GenerateManifestSkill(llm_client))
    registry.register(AcknowledgeIntentSkill())
    
    # 4. Product Kit Skills
    registry.register(GenerateProductKitSkill(llm_client))
    
    # 5. A2A Testing & Verification Skills
    registry.register(PushEcosystemTestsSkill())
    registry.register(GenerateTestReportSkill())
    
    # 6. Transactional Domain Skills
    registry.register(VerifyVpaSkill())
    registry.register(ProcessPostingSkill())
    registry.register(RouteToPartySkill())
    
    # 7. Certification & Compliance Skills
    registry.register(CertifyPillarSkill(llm_client))
    
    return registry
