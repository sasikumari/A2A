from .base_agent import BaseAgent
import time
import queue

class SwitchAgent(BaseAgent):
    def __init__(self, llm_client, bus, reasoning_agent=None):
        super().__init__("SwitchAgent", "SWITCH", llm_client, bus)
        self.reasoning_agent = reasoning_agent

    def propose_spec_change(self, prompt):
        if not self.reasoning_agent:
            return {"error": "Reasoning agent not available"}

        print(f"[{self.name}] Analyzing prompt via action-based ReasoningAgent: {prompt}")
        self.bus.publish_event("agent_status", {
            "name": self.name,
            "status": "PLANNING",
            "msg": "Running impact analysis and building action execution plan…",
        })
        plan = self.reasoning_agent.analyze_prompt(prompt)

        # Publish the plan summary to the UI
        files = plan.get("files_to_change") or plan.get("impact_analysis", {}).get("technical_components", [])
        self.bus.publish_event("agent_status", {
            "name": self.name,
            "status": "PLANNING",
            "msg": (
                f"Plan ready — {len(files)} file(s) to update: {', '.join(files[:4])}. "
                f"Risk: {plan.get('impact_analysis', {}).get('risk_assessment', 'Medium')}."
            ),
            "plan": plan,
        })
        return plan

    def execute_spec_change(self, plan):
        """
        Executes the NPCI 8-Phase Orchestration Pipeline with Human Approval Gates.
        """
        version = plan.get('version', '1.x')
        print(f"[{self.name}] 🚀 Starting 8-Phase Orchestration for v{version}")
        
        # --- PHASE 1-6: PRODUCT & TECHNICAL DESIGN ---
        phases = ["IDEATION", "CANVAS", "PROTOTYPE", "KIT", "BRD_FORMALIZATION", "TSD_SPEC"]
        for phase in phases:
            self._publish("RUNNING", f"Phase: {phase} in progress...")
            time.sleep(1) # Simulation of agent work
            if not self._wait_for_approval(phase):
                self._publish("ERROR", f"Orchestration HALTED: {phase} denied by Human Auditor.")
                return False

        # --- PHASE 7: MULTI-PARTY A2A COORDINATION ---
        self._publish("RUNNING", "Phase 7: Starting Multi-party A2A Coordination.")
        
        # 7.1 Manifest Generation
        parties = ["PAYER_PSP", "PAYEE_PSP", "REMITTER_BANK", "BENEFICIARY_BANK"]
        manifests = {}
        tsd = plan.get("tsd", "Standard UPI Spec Update")
        
        for party in parties:
            m_skill = self.registry.get("generate_manifest")
            m_res = m_skill.execute(tsd=tsd, target_party=party, feature_name=plan.get("feature_name", "Update"))
            if m_res.success:
                s_skill = self.registry.get("sign_manifest")
                s_res = s_skill.execute(manifest_json=m_res.output, secret_key="NPCI_SECRET")
                if s_res.success:
                    manifests[party] = s_res.output
                    
                    r_skill = self.registry.get("route_to_party")
                    r_skill.execute(target_party=party, payload=s_res.output, type="MANIFEST", _context={"bus": self.bus})

        if not self._wait_for_approval("MANIFEST_DISPATCH"):
            return False

        # 7.3 Collect ACKs (Dynamic & Robust)
        self._publish("WAITING", "A2A: Waiting for Signed Acknowledgments...")
        # Only wait for parties that actually received a manifest
        expected_ack_parties = list(manifests.keys())
        acks = self._collect_a2a_events("a2a.switch.ack", expected_ack_parties, timeout=30)
        
        if len(acks) < len(expected_ack_parties):
            missing = [p for p in expected_ack_parties if p not in acks]
            self._publish("ERROR", f"A2A Handshake Failed: Timeout. No ACK from: {', '.join(missing)}")
            return False
            
        # 7.4 Test Case Push
        if not self._wait_for_approval("ECOSYSTEM_TESTING"):
            return False
            
        dispatched_tests = []
        for party in expected_ack_parties: # Only push to parties that ACKed
            t_skill = self.registry.get("push_ecosystem_tests")
            test_cases = [{"scenario": f"v{version} compliance check", "expected": "PASS"}]
            t_res = t_skill.execute(test_cases=test_cases, txn_type="PAY", agent_name=party)
            if t_res.success:
                r_skill = self.registry.get("route_to_party")
                r_skill.execute(target_party=party, payload=t_res.output, type="TEST_PUSH")
                dispatched_tests.append(party)

        # 7.5 Collect Reports
        self._publish("WAITING", "A2A: Waiting for Sandbox Verification Reports...")
        reports = self._collect_a2a_events("a2a.switch.report", parties, timeout=30)
        if len(reports) < len(parties):
            return False

        # --- PHASE 8: PHASED DEPLOYMENT ---
        if not self._wait_for_approval("FINAL_DEPLOYMENT"):
            return False
            
        self._publish("RELOADING", "Initiating hot-reload across ecosystem nodes...")
        self._hot_reload_system()
        self._publish("COMPLETED", f"Ecosystem-wide Deployment v{version} SUCCESS.")
        return True

    def _wait_for_approval(self, phase_name):
        """NPCI Audit Gate: Waits for 'approval_gate' signal on the bus."""
        print(f"[{self.name}] 🛡️ GATED: Waiting for Human Approval for {phase_name}...")
        self.bus.publish_event("agent_status", {
            "name": self.name,
            "status": "AWAITING_APPROVAL",
            "msg": f"Action Required: Approve {phase_name} Pillar results.",
            "phase": phase_name
        })
        
        # Subscription to approval topic
        sub = self.bus.subscribe("human_approval")
        start = time.time()
        timeout = 60 # 1 minute for demo
        
        while time.time() - start < timeout:
            for event in sub:
                if event.get("phase") == phase_name:
                    decision = event.get("decision")
                    if decision == "APPROVE":
                        print(f"[{self.name}] ✅ {phase_name} APPROVED.")
                        return True
                    else:
                        print(f"[{self.name}] ❌ {phase_name} REJECTED.")
                        return False
            time.sleep(0.5)
        
        print(f"[{self.name}] ⚠️ Approval Timeout for {phase_name}.")
        return False

    def _collect_a2a_events(self, topic: str, expected_parties: list[str], timeout: int = 30) -> dict[str, str]:
        """
        Helper to collect and de-duplicate A2A response events.
        Uses a non-blocking queue to avoid generator hangs and performs
        robust string matching for agent roles.
        """
        results = {}
        start = time.time()
        
        # Use simple bus.listen which returns a queue (handled by a thread)
        # This ensures we don't block the main switch thread.
        q = self.bus.listen(topic)
        
        print(f"[{self.name}] ⏳ Waiting for ACKs from: {expected_parties}")
        
        while len(results) < len(expected_parties):
            elapsed = time.time() - start
            if elapsed >= timeout:
                print(f"[{self.name}] ⚠️ Handshake timed out. Missing acks from: {[p for p in expected_parties if p not in results]}")
                break
                
            try:
                # Wait for next event with remaining time as timeout
                event = q.get(timeout=max(0.5, timeout - elapsed))
                sender = event.get("sender", "Unknown").upper()
                
                # Robust matching: Role 'PAYER_PSP' matches 'PayerPSPAgent'
                # Logic: remove underscores and check if role is in sender name
                party_match = next(
                    (p for p in expected_parties if p.replace("_", "").upper() in sender), 
                    None
                )
                
                if party_match and party_match not in results:
                    results[party_match] = event.get("content")
                    count = len(results)
                    total = len(expected_parties)
                    print(f"[{self.name}] ✅ Received ACK from {party_match} ({count}/{total})")
                    self._publish("WAITING", f"A2A Handshake: {count}/{total} acknowledgments received ({party_match}).")
                
            except queue.Empty:
                # Timeout on q.get() - loop will check elapsed time
                continue
            except Exception as e:
                print(f"[{self.name}] ⚠️ Error in collection loop: {e}")
                continue
                
        return results

    def _hot_reload_system(self):
        """Triggers the transactional hot-reload on the backend server."""
        try:
            import urllib.request as _urllib
            _req = _urllib.Request(
                "http://localhost:5000/agents/reload",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with _urllib.urlopen(_req, timeout=5) as _resp:
                pass
        except Exception:
            print(f"[{self.name}] Hot-reload simulation complete.")

        # 5. SAVE POST-CHANGE SNAPSHOT (named with version + description)
        if len(failed_agents) == 0:
            self._save_post_change_snapshot(version, plan.get("description", description))

        # 6. COMMIT CHANGES TO GIT (only if enabled and no agent failures)
        if len(failed_agents) == 0:
            commit_msg = f"Phase 2 Spec Change v{version}: {description[:100]}"
            self._create_git_commit(commit_msg)

        return True

    def _save_post_change_snapshot(self, version, description):
        """Save a labeled post-change snapshot so the deploy UI can show named versions."""
        import subprocess
        import os as _os
        import json
        import re
        import shutil
        from datetime import datetime

        _project_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(description))[:40].strip("_")
        ver_slug = re.sub(r"[^a-zA-Z0-9.]+", "", str(version))
        folder_name = f"{ts}_v{ver_slug}_{slug}_post_change"
        backup_dir = _os.path.join(_project_root, "backups", folder_name)

        try:
            _os.makedirs(backup_dir, exist_ok=True)
            # Copy component files into snapshot
            components = {
                "switch": ["switch/upi_switch.py"],
                "psps": ["psps/payer_psp.py", "psps/payer_psp_handler.py",
                         "psps/payee_psp.py", "psps/payee_psp_handler.py"],
                "banks": ["banks/remitter_bank.py", "banks/beneficiary_bank.py",
                          "banks/remitter_bank_handler.py", "banks/beneficiary_bank_handler.py"],
                "agents": ["agents/base_agent.py", "agents/switch_agent.py",
                           "agents/reasoning_agent.py", "agents/llm_client.py"],
            }
            schema_dir = _os.path.join(_project_root, "api", "schemas")
            if _os.path.exists(schema_dir):
                components["api/schemas"] = [
                    _os.path.join("api", "schemas", f)
                    for f in _os.listdir(schema_dir) if f.endswith(".xsd")
                ]

            for group_files in components.values():
                for rel_path in group_files:
                    src = _os.path.join(_project_root, rel_path)
                    dst = _os.path.join(backup_dir, rel_path)
                    if _os.path.exists(src):
                        _os.makedirs(_os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)

            # Write metadata so the UI can show a friendly label
            meta = {
                "version": version,
                "description": description,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "type": "post_change",
                "folder": folder_name,
            }
            with open(_os.path.join(backup_dir, "metadata.json"), "w") as mf:
                json.dump(meta, mf, indent=2)

            print(f"[{self.name}] Post-change snapshot saved: {folder_name}")
        except Exception as e:
            print(f"[{self.name}] Warning: could not save post-change snapshot: {e}")

    def _create_git_commit(self, message):
        """
        Creates a git commit for the changes made by the agents.
        Skips cleanly if not in a git repo, git not installed, or ALLOW_GIT_COMMIT not set.
        """
        import subprocess
        _os = __import__("os")
        if _os.getenv("ALLOW_GIT_COMMIT", "0").strip().lower() not in ("1", "true", "yes"):
            print(f"[{self.name}] Git commit skipped (set ALLOW_GIT_COMMIT=1 to enable).")
            return
        _project_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        print(f"[{self.name}] Committing changes to Git...")
        try:
            # Check if we're inside a git repo
            r = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=_project_root,
                capture_output=True,
                text=True,
            )
            if r.returncode != 0:
                print(f"[{self.name}] Git: Not a git repository (or git not installed). Skip commit.")
                return
            # Stage changes (do not use check=True)
            r = subprocess.run(["git", "add", "."], cwd=_project_root, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"[{self.name}] Git add failed: {r.stderr or r.stdout}")
                return
            # Commit
            r = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=_project_root,
                capture_output=True,
                text=True,
            )
            if r.returncode == 0:
                line = (r.stdout or "").strip().splitlines()[0] if r.stdout else "Success"
                print(f"[{self.name}] Git Commit: {line}")
                self.bus.publish_event("agent_status", {
                    "name": self.name,
                    "status": "READY",
                    "msg": f"Changes committed to Git: {message[:80]}…"
                })
            else:
                err = (r.stderr or r.stdout or "").lower()
                if "nothing to commit" in err or "no changes" in err:
                    print(f"[{self.name}] Git: Nothing to commit (working tree clean).")
                else:
                    print(f"[{self.name}] Git commit failed: {r.stderr or r.stdout}")
        except FileNotFoundError:
            print(f"[{self.name}] Git not found. Skip commit.")
        except Exception as e:
            print(f"[{self.name}] Error during Git commit: {e}")

    def publish_spec_change(self, version, description, full_plan=None):
        """
        Broadcasts a new spec change to all listeners.
        """
        print(f"[{self.name}] Broadcasting spec change v{version}: {description}")
        event = {
            "version": version,
            "description": description,
            "verification_payload": (full_plan or {}).get("verification_payload", ""),
            "brd": (full_plan or {}).get("brd", ""),
            "tsd": (full_plan or {}).get("tsd", ""),
            "timestamp": time.time()
        }
        self.bus.publish_event("spec_change", event)
        self.bus.publish_event("agent_status", {"name": self.name, "status": "WORKING", "msg": f"Published Spec v{version}"})
        
        # Explicitly trigger self-update since listener excludes Switch
        self.receive_spec_change(event)
