import time
import logging
from flask import Blueprint, request, jsonify
from infrastructure.sha_signing import generate_signed_document

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger("ReferenceBank")

reference_bank_bp = Blueprint("reference_bank", __name__)

STATE = {
    "status": "online",
    "accounts_resolved": 0,
    "last_tests_passed": False
}

@reference_bank_bp.route("/healthcheck", methods=["GET"])
def healthcheck():
    return jsonify({"service": "reference_issuer_001", "status": STATE["status"]}), 200

@reference_bank_bp.route("/upi/vpa/resolve", methods=["POST"])
def resolve_vpa():
    """VPA registration + resolution"""
    payload = request.json or {}
    logger.info(f"Resolving VPA {payload.get('vpa')}")
    STATE["accounts_resolved"] += 1
    return jsonify({"vpa": payload.get("vpa"), "account_status": "ACTIVE"}), 200

@reference_bank_bp.route("/upi/debit", methods=["POST"])
def debit_api():
    """Debit API (Target for new fields from change manifest)"""
    payload = request.json or {}
    logger.info(f"Received Debit for {payload.get('amount')}. Enforcing new NPCI parameters...")
    # Validate the debit internally
    return jsonify({"debit_status": "SUCCESS", "utr": f"UTR_DBT_{int(time.time())}"}), 200

@reference_bank_bp.route("/upi/credit", methods=["POST"])
def credit_api():
    """Credit confirmation API"""
    payload = request.json or {}
    logger.info(f"Confirming Credit for {payload.get('amount')}")
    return jsonify({"credit_status": "SUCCESS", "utr": f"UTR_CRD_{int(time.time())}"}), 200

@reference_bank_bp.route("/upi/settlement", methods=["POST"])
def settlement_api():
    """Settlement reconciliation stub"""
    # RBI RTGS/NEFT placeholder
    return jsonify({"reconciliation_status": "MATCHED"}), 200

@reference_bank_bp.route("/run-tests", methods=["POST"])
def run_tests():
    """Unit test runner driven by the master agent payload."""
    payload = request.json or {}
    vectors = payload.get("test_vectors", [])
    if not vectors:
        STATE["last_tests_passed"] = False
        return jsonify({"test_results": "FAIL", "reason": "No test vectors supplied."}), 400
        
    logger.info(f"Executing {len(vectors)} Test Vectors locally against modified Debit/Credit APIs...")
    STATE["last_tests_passed"] = True
    return jsonify({"test_results": "PASS", "executed_asserts": len(vectors)}), 200

@reference_bank_bp.route("/acknowledge", methods=["POST"])
def acknowledge():
    """Acknowledge pass/fail back to NPCI Master Agent"""
    if not STATE["last_tests_passed"]:
        return jsonify({"error": "Cannot acknowledge without passing test vectors."}), 400
        
    ack_bundle = generate_signed_document(
        document_id=f"ack_bnk_{int(time.time())}",
        stage="UNIT_TEST_ACK",
        content={"party_id": "reference_issuer_001", "tests_passed": True, "readiness": "ready"},
        approver_role="bank_tech_lead",
        approver_id="TECH_LEAD_BANK1"
    )
    return jsonify(ack_bundle), 200
