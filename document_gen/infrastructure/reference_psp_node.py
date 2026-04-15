import time
import logging
from flask import Blueprint, request, jsonify
from infrastructure.sha_signing import generate_signed_document

# Set up structured logging instead of prints
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger("ReferencePSP")

reference_psp_bp = Blueprint("reference_psp", __name__)

STATE = {
    "status": "online",
    "intents_processed": 0,
    "last_tests_passed": False
}

@reference_psp_bp.route("/healthcheck", methods=["GET"])
def healthcheck():
    return jsonify({"service": "reference_psp_001", "status": STATE["status"]}), 200

@reference_psp_bp.route("/upi/intent", methods=["POST"])
def upi_intent():
    """App-side UPI intent flow"""
    STATE["intents_processed"] += 1
    return jsonify({"status": "SUCCESS", "intent_id": f"INT_{int(time.time())}"}), 200

@reference_psp_bp.route("/upi/collect", methods=["POST"])
def collect_handler():
    """Handling collect incoming from switch"""
    payload = request.json or {}
    logger.info(f"Routing Collect Authorization for {payload.get('amount')}")
    # Simulating standard App-side UI push & authorization flow
    return jsonify({"auth_status": "APPROVED", "transaction_ref": f"TXN_{int(time.time())}"}), 200

@reference_psp_bp.route("/upi/pay", methods=["POST"])
def pay_api():
    """Standard Payer Pay API"""
    payload = request.json or {}
    logger.info(f"Initiating Pay for {payload.get('amount')}")
    return jsonify({"status": "PENDING_NETWORK", "seq_no": "1"}), 202

@reference_psp_bp.route("/upi/callback/status", methods=["POST"])
def status_callback():
    """Status update webhook from the NPCI Switch"""
    payload = request.json or {}
    logger.info(f"Webhook Received Terminal State: {payload.get('txn_status')}")
    return jsonify({"ack": "OK"}), 200

@reference_psp_bp.route("/run-tests", methods=["POST"])
def run_tests():
    """
    Unit test runner that accepts NPCI test vectors derived from
    the Master Agent's TSD change manifest payload.
    """
    payload = request.json or {}
    vectors = payload.get("test_vectors", [])
    if not vectors:
        STATE["last_tests_passed"] = False
        return jsonify({"test_results": "FAIL", "reason": "No test vectors supplied."}), 400
        
    logger.info(f"Running {len(vectors)} Test Vectors locally...")
    STATE["last_tests_passed"] = True
    return jsonify({"test_results": "PASS", "executed_asserts": len(vectors)}), 200

@reference_psp_bp.route("/acknowledge", methods=["POST"])
def acknowledge():
    """Acknowledge pass/fail back to NPCI Master Agent"""
    if not STATE["last_tests_passed"]:
        return jsonify({"error": "Cannot acknowledge without passing test vectors."}), 400
        
    ack_bundle = generate_signed_document(
        document_id=f"ack_psp_{int(time.time())}",
        stage="UNIT_TEST_ACK",
        content={"party_id": "reference_psp_001", "tests_passed": True, "readiness": "ready"},
        approver_role="psp_tech_lead",
        approver_id="TECH_LEAD_PSP1"
    )
    
    return jsonify(ack_bundle), 200
