import json
import uuid

class NPCIMasterAgent:
    """
    Role: Translate approved BRD into Technical Specification Documents (TSD)
    with per-party API-level specifications and strict JSON change manifests.
    """
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def translate_brd_to_tsd(self, brd: dict) -> dict:
        system = """You are the NPCI Master Technical Architect.
You receive a Business Requirements Document (BRD) and must produce a comprehensive Technical Specification Document (TSD) with per-party API-level specifications.

The TSD MUST follow this exact structure in the "tsd" field (Markdown):

# Technical Specification Document (TSD)
## 1. Architecture Overview
   - System topology, data flow, integration layer

## 2. Per-Party Technical Changes

### 2.1 PAYER_PSP Changes
- **API Endpoint:** e.g. POST /upi/v2/pay/initiate
- **Request Schema Changes:** List each added/modified/removed field with data type, max length, validation regex
- **Response Schema Changes:** New fields, modified status codes
- **Business Rules:** Specific enforcement logic
- **Error Codes Added:** Code, description, HTTP status
- **Sequence Diagram Delta:** Step-by-step change in call flow

### 2.2 PAYEE_PSP Changes
(Same structure as 2.1)

### 2.3 REMITTER_BANK Changes
(Same structure as 2.1)

### 2.4 BENEFICIARY_BANK Changes
(Same structure as 2.1)

## 3. XML Schema Changes (XSD Delta)
   - Specific elements added/modified/removed in upi_pay_request.xsd

## 4. Backward Compatibility Matrix
   | Party | Compatible? | Migration Required | Timeline |

## 5. Deployment Rollout Plan
   - Phase 1 (Pilot), Phase 2 (Scaled), Phase 3 (Full rollout) with dates and participants

Return ONLY valid JSON with exactly this structure:
{
  "tsd": "## Full Markdown TSD following the structure above (all 5 sections, all 4 parties)...",
  "change_manifests": [
    {
      "party_id": "PAYER_PSP",
      "party_type": "payer_psp",
      "changes": [
        {
          "api_endpoint": "/upi/v2/pay/initiate",
          "http_method": "POST",
          "change_type": "parameter_addition | parameter_modification | parameter_removal | new_endpoint",
          "field": "fieldName",
          "data_type": "string | integer | boolean | object",
          "max_length": 64,
          "validation_rules": "Regex or specific constraint e.g. ^[0-9]{4,6}$ for PIN",
          "business_rule": "Specific NPCI business logic being enforced",
          "example_request": "{ ... }",
          "example_response": "{ ... }",
          "test_vectors": ["<valid_xml_or_json_test_vector_1>", "<invalid_test_vector_for_error>"],
          "backward_compatible": true,
          "required_by": "2025-Q4"
        }
      ],
      "sequence_diagram_delta": "Step N: PAYER_PSP now calls X before Y to ensure Z",
      "error_codes_added": [
        { "code": "UPI301", "description": "...", "http_status": 422 }
      ]
    },
    {
      "party_id": "PAYEE_PSP",
      "party_type": "payee_psp",
      "changes": [],
      "sequence_diagram_delta": "",
      "error_codes_added": []
    },
    {
      "party_id": "REMITTER_BANK",
      "party_type": "remitter_bank",
      "changes": [],
      "sequence_diagram_delta": "",
      "error_codes_added": []
    },
    {
      "party_id": "BENEFICIARY_BANK",
      "party_type": "beneficiary_bank",
      "changes": [],
      "sequence_diagram_delta": "",
      "error_codes_added": []
    }
  ]
}
"""
        response = self.llm_client.query(json.dumps(brd), system=system, max_tokens=4096)
        try:
            import re
            # Strip think tags if present (for reasoning models)
            response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
            start = response.find('{')
            end = response.rfind('}')
            return json.loads(response[start:end + 1])
        except Exception:
            return {
                "tsd": "Failed to generate TSD from BRD.",
                "change_manifests": []
            }
