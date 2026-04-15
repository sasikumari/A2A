"""
System operation skills — run tests, hot-reload, git commit, shell commands.
"""

from __future__ import annotations
import os
import subprocess
from . import Skill, SkillResult


class RunTestsSkill(Skill):
    name = "run_tests"
    description = (
        "Execute the automated test suite against the running UPI server. "
        "Returns pass/fail status and stdout output."
    )
    parameters = {
        "type": "object",
        "properties": {
            "project_root": {
                "type": "string",
                "description": "Absolute path to the project root.",
            },
            "test_args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional args to pass to tools/run_tests.py (default: ['--all']).",
            },
        },
        "required": ["project_root"],
    }

    def execute(self, project_root: str, test_args: list = None, **_) -> SkillResult:
        args = test_args or ["--all"]
        cmd = ["python3", "tools/run_tests.py"] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root,
                env={**os.environ, "PYTHONPATH": project_root},
                timeout=120,
            )
            output = result.stdout + (("\n" + result.stderr) if result.stderr else "")
            passed = result.returncode == 0
            return SkillResult(
                success=passed,
                output=output.strip()[:2000],
                error=None if passed else f"Tests failed (exit code {result.returncode})",
                metadata={"returncode": result.returncode},
            )
        except subprocess.TimeoutExpired:
            return SkillResult(success=False, error="Test suite timed out after 120s.")
        except Exception as e:
            return SkillResult(success=False, error=str(e))


class HotReloadSkill(Skill):
    name = "hot_reload"
    description = (
        "POST to the running server's /agents/reload endpoint to apply "
        "in-memory updates (new limit values, patched logic) without restarting."
    )
    parameters = {
        "type": "object",
        "properties": {
            "server_url": {
                "type": "string",
                "description": "Base URL of the running server (default: http://localhost:5000).",
            }
        },
        "required": [],
    }

    def execute(self, server_url: str = "http://localhost:5000", **_) -> SkillResult:
        import urllib.request
        import json
        url = f"{server_url.rstrip('/')}/agents/reload"
        try:
            req = urllib.request.Request(
                url,
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            return SkillResult(
                success=True,
                output=f"Hot-reload OK: P2P={data.get('P2P_LIMIT', '?')}, MAX={data.get('MAX_TXN_AMOUNT', '?')}",
                metadata=data,
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=f"Hot-reload failed: {e} — server may need manual restart.",
            )


class GitCommitSkill(Skill):
    name = "git_commit"
    description = (
        "Stage all changed files and create a git commit. "
        "Only runs if ALLOW_GIT_COMMIT=1 env var is set. "
        "Skips cleanly if not in a git repo."
    )
    parameters = {
        "type": "object",
        "properties": {
            "project_root": {
                "type": "string",
                "description": "Absolute path to the project root (git working directory).",
            },
            "message": {
                "type": "string",
                "description": "Commit message.",
            },
        },
        "required": ["project_root", "message"],
    }

    def execute(self, project_root: str, message: str, **_) -> SkillResult:
        if os.getenv("ALLOW_GIT_COMMIT", "0").strip().lower() not in ("1", "true", "yes"):
            return SkillResult(
                success=True,
                output="Git commit skipped (set ALLOW_GIT_COMMIT=1 to enable).",
            )

        try:
            r = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=project_root,
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                return SkillResult(success=True, output="Not a git repo — skipping commit.")

            subprocess.run(["git", "add", "."], cwd=project_root, check=True)
            r = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=project_root, capture_output=True, text=True,
            )
            if r.returncode == 0:
                line = (r.stdout or "").strip().splitlines()[0] if r.stdout else "committed"
                return SkillResult(success=True, output=f"Git: {line}")

            err = (r.stderr or r.stdout or "").lower()
            if "nothing to commit" in err:
                return SkillResult(success=True, output="Git: nothing to commit.")
            return SkillResult(success=False, error=f"Git commit failed: {r.stderr or r.stdout}")

        except FileNotFoundError:
            return SkillResult(success=True, output="Git not installed — skipping commit.")
        except Exception as e:
            return SkillResult(success=False, error=str(e))


class CreateBackupSnapshotSkill(Skill):
    name = "create_backup_snapshot"
    description = (
        "Save a named post-change snapshot of all component files so the deploy "
        "UI can show labeled versions and roll back if needed."
    )
    parameters = {
        "type": "object",
        "properties": {
            "project_root": {
                "type": "string",
                "description": "Project root path.",
            },
            "version": {
                "type": "string",
                "description": "Version string (e.g. '1.5').",
            },
            "description": {
                "type": "string",
                "description": "Short description of the change.",
            },
            "snapshot_type": {
                "type": "string",
                "description": "'pre_change' or 'post_change'.",
            },
        },
        "required": ["project_root", "version", "description"],
    }

    def execute(
        self,
        project_root: str,
        version: str,
        description: str,
        snapshot_type: str = "post_change",
        **_,
    ) -> SkillResult:
        import json
        import re
        import shutil
        from datetime import datetime

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(description))[:40].strip("_")
        ver_slug = re.sub(r"[^a-zA-Z0-9.]+", "", str(version))
        folder_name = f"{ts}_v{ver_slug}_{slug}_{snapshot_type}"
        backup_dir = os.path.join(project_root, "backups", folder_name)

        components = {
            "switch": ["switch/upi_switch.py"],
            "psps": [
                "psps/payer_psp.py", "psps/payer_psp_handler.py",
                "psps/payee_psp.py", "psps/payee_psp_handler.py",
            ],
            "banks": [
                "banks/remitter_bank.py", "banks/beneficiary_bank.py",
                "banks/remitter_bank_handler.py", "banks/beneficiary_bank_handler.py",
            ],
            "agents": [
                "agents/base_agent.py", "agents/switch_agent.py",
                "agents/reasoning_agent.py", "agents/llm_client.py",
            ],
        }
        schema_dir = os.path.join(project_root, "api", "schemas")
        if os.path.exists(schema_dir):
            components["api/schemas"] = [
                os.path.join("api", "schemas", f)
                for f in os.listdir(schema_dir) if f.endswith(".xsd")
            ]

        try:
            os.makedirs(backup_dir, exist_ok=True)
            copied = []
            for group_files in components.values():
                for rel_path in group_files:
                    src = os.path.join(project_root, rel_path)
                    dst = os.path.join(backup_dir, rel_path)
                    if os.path.exists(src):
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        copied.append(rel_path)

            meta = {
                "version": version,
                "description": description,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "type": snapshot_type,
                "folder": folder_name,
            }
            with open(os.path.join(backup_dir, "metadata.json"), "w") as mf:
                json.dump(meta, mf, indent=2)

            return SkillResult(
                success=True,
                output=f"Snapshot saved: {folder_name}",
                metadata={"folder": folder_name, "files_copied": len(copied)},
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))


class RunCommandSkill(Skill):
    name = "run_command"
    description = (
        "Execute an arbitrary shell command in the project root. "
        "Use sparingly — prefer specific skills. "
        "Returns stdout, stderr, and exit code."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Command as list of tokens (e.g. ['python3', 'tools/check.py']).",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 60).",
            },
        },
        "required": ["command"],
    }

    def execute(self, command: list, cwd: str = ".", timeout: int = 60, **_) -> SkillResult:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=cwd,
                env={**os.environ},
                timeout=timeout,
            )
            output = (result.stdout + "\n" + result.stderr).strip()
            return SkillResult(
                success=result.returncode == 0,
                output=output[:2000],
                error=None if result.returncode == 0 else f"Exit code {result.returncode}",
                metadata={"returncode": result.returncode},
            )
        except subprocess.TimeoutExpired:
            return SkillResult(success=False, error=f"Command timed out after {timeout}s.")
        except Exception as e:
            return SkillResult(success=False, error=str(e))
