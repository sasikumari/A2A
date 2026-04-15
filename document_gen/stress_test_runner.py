import subprocess
import time
import requests
import os
import signal
import sys

# Configuration
BASE_URL = "http://localhost:5000"
APP_CMD = ["python3", "-u", "api/app.py"]
ENV = os.environ.copy()
ENV["PYTHONPATH"] = os.getcwd()
ENV["DISABLE_BUS"] = "0"
ENV["USE_IN_MEMORY_BUS"] = "1"

# Test Scenarios
SCENARIOS = [
    {
        "name": "Risk Score",
        "prompt": "Implement a Risk Score system. 1. Add <Risk><Score>val</Score></Risk> to ReqPay. 2. Payer PSP must calculate this: if Payer addr contains 'risk', score is 90, else 10. 3. Remitter Bank must REJECT transaction if Risk Score > 80.",
        "verify_file": "psps/payee_psp_handler.py", # Note: Logic might end up in payee or payer depending on agent
        "verify_content": "risk_score"
    },
    {
        "name": "Geo-Location",
        "prompt": "Add Geo-Location tracking. 1. Add <Geo><Lat/><Long/></Geo> to ReqPay. 2. Payer PSP should populate dummy values (12.97, 77.59). 3. Switch should log the location.",
        "verify_file": "api/schemas/upi_pay_request.xsd",
        "verify_content": "Geo"
    },
    {
        "name": "High Value Flag",
        "prompt": "Add High Value Flag. 1. Add <HighValue>true/false</HighValue> to ReqPay. 2. Payer PSP sets true if Amount > 100000. 3. Switch logs warning.",
        "verify_file": "api/schemas/upi_pay_request.xsd",
        "verify_content": "HighValue"
    },
    {
        "name": "Merchant Category Code",
        "prompt": "Add MCC to Payee. 1. Add <MCC>code</MCC> to Payee tag. 2. Payee PSP should inject '5411' (Grocery). 3. Remitter Bank should reject if MCC is '6011' (Cash).",
        "verify_file": "api/schemas/upi_pay_request.xsd",
        "verify_content": "MCC"
    },
    {
        "name": "Device OS Check",
        "prompt": "Add Device OS. 1. Add <Device><OS>name</OS></Device>. 2. Payer PSP injects 'Android'. 3. Switch rejects 'Unknown'.",
        "verify_file": "api/schemas/upi_pay_request.xsd",
        "verify_content": "Device"
    },
    {
        "name": "Mandate ID",
        "prompt": "Add Mandate Block. 1. Add <Mandate><Id>val</Id></Mandate>. 2. Payer PSP generates UUID.",
        "verify_file": "api/schemas/upi_pay_request.xsd",
        "verify_content": "Mandate"
    },
    {
        "name": "Tip Amount",
        "prompt": "Add Tip Amount. 1. Add <Tip>val</Tip>. 2. Switch validates Total = Amount + Tip.",
        "verify_file": "api/schemas/upi_pay_request.xsd",
        "verify_content": "Tip"
    },
    {
        "name": "Currency Validation",
        "prompt": "Enforce Currency. 1. Add <Currency>code</Currency>. 2. Switch rejects if not 'INR'.",
        "verify_file": "api/schemas/upi_pay_request.xsd",
        "verify_content": "Currency"
    },
    {
        "name": "Session ID",
        "prompt": "Add Session ID. 1. Add <SessionId>val</SessionId>. 2. Pass through all hops.",
        "verify_file": "api/schemas/upi_pay_request.xsd",
        "verify_content": "SessionId"
    },
    {
        "name": "Encrypted Block",
        "prompt": "Add Encrypted Data. 1. Add <EncData>base64</EncData>. 2. Payer PSP injects dummy base64.",
        "verify_file": "api/schemas/upi_pay_request.xsd",
        "verify_content": "EncData"
    }
]

def wait_for_app():
    retries = 30
    while retries > 0:
        try:
            requests.get(f"{BASE_URL}/phase2")
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            retries -= 1
    return False

def kill_app():
    subprocess.run(["fuser", "-k", "5000/tcp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def run_test(scenario, index):
    print(f"\n=== Running Test {index+1}: {scenario['name']} ===")
    
    # 1. Start App
    print("[Runner] Starting App...")
    kill_app() # Ensure clean slate
    
    log_file = open("runner_app.log", "w")
    process = subprocess.Popen(APP_CMD, env=ENV, stdout=log_file, stderr=subprocess.STDOUT)
    
    if not wait_for_app():
        print("[Runner] ❌ App failed to start")
        process.kill()
        return False

    try:
        # 2. Propose Change
        print("[Runner] Proposing Change...")
        res = requests.post(f"{BASE_URL}/agents/propose-change", json={"prompt": scenario["prompt"]})
        if res.status_code != 200:
            print(f"[Runner] ❌ Proposal failed: {res.text}")
            return False
        plan = res.json()
        
        # 3. Approve Change
        print("[Runner] Approving Change...")
        res = requests.post(f"{BASE_URL}/agents/approve-change", json=plan)
        if res.status_code != 200:
            print(f"[Runner] ❌ Approval failed: {res.text}")
            return False
            
        # 4. Wait for Agents
        print("[Runner] Waiting 45s for agents to update code...")
        time.sleep(45)
        
        # 5. Verify
        print(f"[Runner] Verifying {scenario['verify_file']} contains '{scenario['verify_content']}'...")
        if not os.path.exists(scenario['verify_file']):
             print(f"[Runner] ❌ File {scenario['verify_file']} does not exist")
             return False
             
        with open(scenario['verify_file'], 'r') as f:
            content = f.read()
            
        if scenario['verify_content'] in content:
            print(f"[Runner] ✅ Test {index+1} PASSED")
            return True
        else:
            print(f"[Runner] ❌ Verification Failed. Content not found.")
            return False

    except Exception as e:
        print(f"[Runner] ❌ Exception: {e}")
        return False
    finally:
        print("[Runner] Stopping App...")
        process.terminate()
        kill_app()

def main():
    print("Starting Automated Stress Test Runner...")
    results = []
    
    for i, scenario in enumerate(SCENARIOS):
        success = run_test(scenario, i)
        results.append((scenario['name'], success))
        time.sleep(2) # Cooldown
        
    print("\n\n=== Final Results ===")
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")

if __name__ == "__main__":
    main()
