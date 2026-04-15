
import requests
import json
import time
import subprocess

BASE_URL = "http://127.0.0.1:5000"

def test_auto_commit():
    print("Starting auto-commit verification test...")
    
    # 1. Propose a trivial change
    prompt = "Update the note in reqpay_demo.xml to 'verified versioning'"
    print(f"Proposing change: {prompt}")
    
    try:
        resp = requests.post(f"{BASE_URL}/agents/propose-change", json={"prompt": prompt})
        if resp.status_code != 200:
            print(f"Failed to propose change: {resp.text}")
            return
        
        plan = resp.json()
        print("Plan received. Approving change...")
        
        # 2. Approve the change
        resp = requests.post(f"{BASE_URL}/agents/approve-change", json=plan)
        if resp.status_code != 200:
            print(f"Failed to approve change: {resp.text}")
            return
        
        print("Approval sent. Waiting for agent to finish (polling status)...")
        # Polling isn't strictly necessary for the agent to finish in the background, 
        # but we wait for it to actually do the work.
        
        # Give it some time to process
        for i in range(30):
            time.sleep(2)
            # Check git log
            result = subprocess.run(["git", "log", "-1"], capture_output=True, text=True)
            if "Phase 2 Spec Change" in result.stdout:
                print("SUCCESS: Automatic git commit detected!")
                print(result.stdout)
                return
            print(f"Waiting... ({i*2}s)")
            
        print("FAILURE: Timed out waiting for automatic git commit.")

    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    # Ensure the server is running or this will fail
    test_auto_commit()
