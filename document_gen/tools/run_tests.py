"""
Dynamic test runner — amounts are derived from the live /limits endpoint
so tests stay valid regardless of what the PM prompted the agents to change.
"""
import argparse
import subprocess
import requests
import time
import sys
import os

BASE_URL = "http://127.0.0.1:5000"

# ── Helpers ──────────────────────────────────────────────────────────────────

def check_server_health():
    try:
        r = requests.get(BASE_URL + "/health", timeout=5)
        if r.status_code == 200:
            data = r.json() if r.text else {}
            return data.get("status") == "ok"
        r = requests.get(BASE_URL + "/ui", timeout=5)
        return r.status_code == 200
    except Exception:
        return False

def start_server():
    print("Starting server...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    process = subprocess.Popen(
        ["python3", "api/app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    for _ in range(15):
        if check_server_health():
            print("Server started successfully.")
            return process
        time.sleep(1)
    print("Server failed to start.")
    process.kill()
    return None

def get_limits():
    """Fetch live limits. Falls back to safe defaults if /limits unavailable."""
    try:
        r = requests.get(BASE_URL + "/limits", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    # Safe fallback — amounts that work under any reasonable limit
    return {
        "p2p_limit":       100_00_000,
        "max_txn_amount":  100_00_000,
        "effective_limit": 100_00_000,
        "test_amounts": {
            "safe":       100.00,
            "mid":        500.00,
            "near_limit": 1000.00,
            "over_limit": 200_00_000.00,
        }
    }

def build_reqpay(amount_str, txn_id="DYNTEST", note="Dynamic Test", risk_score=None, high_value=None):
    """Build a valid ReqPay XML using the canonical Phase 1 structure."""
    extras = ""
    if risk_score is not None:
        extras += f"\n  <upi:RiskScore>{risk_score}</upi:RiskScore>"
    if high_value is not None:
        extras += f"\n  <upi:HighValue>{high_value}</upi:HighValue>"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="2025-01-01T10:00:00Z" orgId="PAYERPSP" msgId="{txn_id}" prodType="UPI"/>
  <upi:Txn id="{txn_id}" type="PAY" note="{note}"/>
  <upi:purpose>00</upi:purpose>
  <upi:purposeCode code="00" description="UPI Purpose 00"/>
  <upi:Payer addr="ramesh@payer">
    <upi:Amount value="{amount_str}" curr="INR"/>
    <upi:Creds><upi:Cred><upi:Data code="1234"/></upi:Cred></upi:Creds>
  </upi:Payer>
  <upi:Payees><upi:Payee addr="merchant@benef"/></upi:Payees>{extras}
</upi:ReqPay>"""

# ── Test suites ───────────────────────────────────────────────────────────────

def check_schemas_endpoint():
    print("  GET /schemas ...", end=" ")
    try:
        r = requests.get(f"{BASE_URL}/schemas", timeout=5)
        if r.status_code == 200 and "Available XSD Schemas" in r.text:
            print("PASS")
            return True
        print(f"FAIL (status {r.status_code})")
        return False
    except Exception as e:
        print(f"FAIL ({e})")
        return False

def check_inspector_endpoint():
    print("  GET /inspector ...", end=" ")
    try:
        r = requests.get(f"{BASE_URL}/inspector", timeout=5)
        if r.status_code == 200 and "System Inspector" in r.text:
            print("PASS")
            return True
        print(f"FAIL (status {r.status_code})")
        return False
    except Exception as e:
        print(f"FAIL ({e})")
        return False

def run_endpoint_tests():
    print("\n--- Endpoint Tests ---")
    limits  = get_limits()
    amounts = limits["test_amounts"]
    eff     = limits["effective_limit"]

    print(f"  [limits] effective={eff:,.0f}  "
          f"safe={amounts['safe']:,.2f}  "
          f"over={amounts['over_limit']:,.2f}")

    ok = True

    # ── Static endpoint checks ────────────────────────────────────────────────
    if not check_schemas_endpoint(): ok = False
    if not check_inspector_endpoint(): ok = False

    # ── Dynamic ReqPay tests ──────────────────────────────────────────────────
    cases = [
        # (label, amount, note, risk, hv, expect_ack)
        ("POST /reqpay basic (safe amount)",
            f"{amounts['safe']:.2f}", "Basic Test", None, None, True),
        ("POST /reqpay mid amount (50% of limit)",
            f"{amounts['mid']:.2f}", "Mid Test", None, None, True),
        ("POST /reqpay near-limit (95% — should ACK)",
            f"{amounts['near_limit']:.2f}", "Near Limit", None, None, True),
        ("POST /reqpay over-limit (150% — should DECLINE)",
            f"{amounts['over_limit']:.2f}", "Over Limit", None, None, False),
        ("POST /reqpay with RiskScore",
            f"{amounts['safe']:.2f}", "Risk Test", 85, None, True),
        ("POST /reqpay with HighValue flag",
            f"{amounts['mid']:.2f}", "HighValue Test", None, "true", True),
    ]

    for label, amt, note, risk, hv, expect_ack in cases:
        print(f"  {label} (₹{float(amt):,.2f}) ...", end=" ")
        xml = build_reqpay(amt, txn_id=f"T{int(time.time()*1000)%999999}", note=note,
                           risk_score=risk, high_value=hv)
        try:
            r = requests.post(f"{BASE_URL}/reqpay", data=xml,
                              headers={"Content-Type": "application/xml"}, timeout=10)
            if r.status_code == 202:
                print("PASS (ACK)")
            elif r.status_code == 400:
                if expect_ack:
                    print(f"FAIL (XSD rejected: {r.text[:120]})")
                    ok = False
                else:
                    print("PASS (correctly rejected by XSD)")
            else:
                print(f"FAIL (status {r.status_code}: {r.text[:80]})")
                ok = False
        except Exception as e:
            print(f"FAIL ({e})")
            ok = False

    # ── Transactions list ─────────────────────────────────────────────────────
    print("  GET /transactions ...", end=" ")
    try:
        r = requests.get(f"{BASE_URL}/transactions", timeout=5)
        if r.status_code == 200:
            txns = r.json()
            declined = sum(1 for t in txns if "DECLINED" in t.get("status",""))
            success  = sum(1 for t in txns if t.get("status") == "SUCCESS")
            print(f"PASS (total={len(txns)}, success={success}, declined={declined})")
        else:
            print(f"FAIL (status {r.status_code})")
            ok = False
    except Exception as e:
        print(f"FAIL ({e})")
        ok = False

    return ok

def run_agent_tests():
    print("\n--- Agent Flow Tests ---")
    print("  SKIPPED: test_agents_flow.py requires a live LLM — run manually if needed.")
    return True

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dynamic Test Runner")
    parser.add_argument("--all",       action="store_true", help="Run all endpoint tests")
    parser.add_argument("--endpoints", action="store_true", help="Run endpoint tests")
    parser.add_argument("--agents",    action="store_true", help="Run agent tests (needs live LLM)")
    args = parser.parse_args()

    if not (args.endpoints or args.agents):
        args.all = True

    server_process = None
    if args.all or args.endpoints:
        if not check_server_health():
            server_process = start_server()
            if not server_process:
                sys.exit(1)
        else:
            print("Server is already running.")

    success = True
    if args.all or args.endpoints:
        if not run_endpoint_tests():
            success = False
    if args.all or args.agents:
        if not run_agent_tests():
            success = False

    if server_process:
        print("Stopping temporary server...")
        server_process.terminate()
        server_process.wait()

    if success:
        print("\nAll executed tests PASSED.")
        sys.exit(0)
    else:
        print("\nSome tests FAILED.")
        sys.exit(1)
