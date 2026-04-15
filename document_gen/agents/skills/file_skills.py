"""
File operation skills — read, write, patch, rollback.
These are the fundamental I/O building blocks for every agent.
"""

from __future__ import annotations
import os
import re
from . import Skill, SkillResult


class ReadFileSkill(Skill):
    name = "read_file"
    description = (
        "Read the current contents of a source file from disk. "
        "Returns the full text content. Must be called before writing or patching."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute or project-relative path to the file.",
            }
        },
        "required": ["file_path"],
    }

    def execute(self, file_path: str, **_) -> SkillResult:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return SkillResult(
                success=True,
                output=content,
                metadata={"path": file_path, "size": len(content), "lines": content.count("\n")},
            )
        except FileNotFoundError:
            return SkillResult(success=False, error=f"File not found: {file_path}")
        except Exception as e:
            return SkillResult(success=False, error=str(e))


class WriteFileSkill(Skill):
    name = "write_file"
    description = (
        "Write new content to a file (full replacement). "
        "Creates the file if it does not exist. "
        "Always backup_first before writing to existing files."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to write.",
            },
            "content": {
                "type": "string",
                "description": "Full new content to write to the file.",
            },
        },
        "required": ["file_path", "content"],
    }

    def execute(self, file_path: str, content: str, **_) -> SkillResult:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return SkillResult(
                success=True,
                output=f"Written {len(content)} bytes to {file_path}",
                metadata={"path": file_path, "size": len(content)},
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))


class BackupFileSkill(Skill):
    name = "backup_file"
    description = (
        "Create a .bak copy of a file before modifying it. "
        "Must be called before write_file or apply_patch on any existing file. "
        "Returns the backup path."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to back up.",
            }
        },
        "required": ["file_path"],
    }

    def execute(self, file_path: str, **_) -> SkillResult:
        if not os.path.exists(file_path):
            return SkillResult(success=False, error=f"Cannot backup non-existent file: {file_path}")
        backup_path = f"{file_path}.bak"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(content)
            return SkillResult(
                success=True,
                output=backup_path,
                metadata={"original": file_path, "backup": backup_path, "size": len(content)},
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))


class RollbackFileSkill(Skill):
    name = "rollback_file"
    description = (
        "Restore a file from its .bak backup. "
        "Use when a write or patch produced a broken file and verification failed."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to roll back (the .bak will be restored).",
            }
        },
        "required": ["file_path"],
    }

    def execute(self, file_path: str, **_) -> SkillResult:
        backup_path = f"{file_path}.bak"
        if not os.path.exists(backup_path):
            return SkillResult(success=False, error=f"No backup found at {backup_path}")
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                content = f.read()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return SkillResult(
                success=True,
                output=f"Rolled back {file_path} from {backup_path}",
                metadata={"file": file_path, "backup": backup_path},
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))


class ApplyPatchSkill(Skill):
    name = "apply_patch"
    description = (
        "Apply a SEARCH/REPLACE patch to a file without rewriting the whole file. "
        "The patch must use the exact format:\n"
        "<<<< SEARCH\n<exact lines to find>\n====\n<replacement lines>\n>>>>\n"
        "Multiple blocks are applied in sequence. "
        "SEARCH content must match the file exactly including indentation."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to patch.",
            },
            "patch": {
                "type": "string",
                "description": "Patch content with one or more SEARCH/REPLACE blocks.",
            },
        },
        "required": ["file_path", "patch"],
    }

    def execute(self, file_path: str, patch: str, **_) -> SkillResult:
        if not os.path.exists(file_path):
            return SkillResult(success=False, error=f"File not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                current = f.read()
        except Exception as e:
            return SkillResult(success=False, error=f"Could not read file: {e}")

        blocks = re.findall(r"<<<< SEARCH\n(.*?)\n====\n(.*?)\n>>>>", patch, re.DOTALL)
        if not blocks:
            return SkillResult(success=False, error="No valid SEARCH/REPLACE blocks found in patch.")

        updated = current
        applied = 0
        for search_text, replace_text in blocks:
            search_lines = [l.rstrip() for l in search_text.splitlines()]
            file_lines = updated.splitlines()

            match_idx = -1
            for i in range(len(file_lines) - len(search_lines) + 1):
                window = [l.rstrip() for l in file_lines[i: i + len(search_lines)]]
                if window == search_lines:
                    match_idx = i
                    break

            if match_idx == -1:
                return SkillResult(
                    success=False,
                    error=(
                        f"SEARCH block #{applied + 1} did not match any content in {file_path}. "
                        f"Ensure exact whitespace/indentation match.\n"
                        f"Search snippet: {search_text[:120]!r}"
                    ),
                )

            new_lines = (
                file_lines[:match_idx]
                + replace_text.splitlines()
                + file_lines[match_idx + len(search_lines):]
            )
            updated = "\n".join(new_lines)
            applied += 1

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated)
        except Exception as e:
            return SkillResult(success=False, error=f"Could not write patched file: {e}")

        return SkillResult(
            success=True,
            output=updated,
            metadata={"file": file_path, "blocks_applied": applied},
        )


class ListFilesSkill(Skill):
    name = "list_files"
    description = (
        "List all files in a directory (non-recursive). "
        "Useful for discovering what files an agent manages."
    )
    parameters = {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Directory path to list.",
            },
            "extension_filter": {
                "type": "string",
                "description": "Optional file extension filter (e.g. '.py', '.xsd').",
            },
        },
        "required": ["directory"],
    }

    def execute(self, directory: str, extension_filter: str = "", **_) -> SkillResult:
        if not os.path.isdir(directory):
            return SkillResult(success=False, error=f"Not a directory: {directory}")
        try:
            files = [
                os.path.join(directory, f)
                for f in sorted(os.listdir(directory))
                if os.path.isfile(os.path.join(directory, f))
                and (not extension_filter or f.endswith(extension_filter))
            ]
            return SkillResult(success=True, output=files, metadata={"count": len(files)})
        except Exception as e:
            return SkillResult(success=False, error=str(e))
