"""Precise document section editor.

Loads an existing .docx (via generated_sections.json artifact),
regenerates only the requested section with a user edit instruction,
and re-assembles a new version of the document.

Usage:
    from app.tools.document_editor import edit_document_section
    new_path = edit_document_section(job_id, section_heading, edit_instruction)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_artifact(job_id: str, name: str) -> Any:
    """Load a JSON artifact from the job's output directory."""
    from app.config import settings
    path = Path(settings.output_dir) / job_id / name
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def edit_document_section(
    job_id: str,
    section_heading: str,
    edit_instruction: str,
    output_suffix: str = "_edited",
) -> str:
    """Regenerate a single section of an existing document.

    Args:
        job_id:            Job ID whose artifacts (plan + sections) will be loaded.
        section_heading:   Exact or case-insensitive heading of the section to edit.
        edit_instruction:  Natural language instruction describing the edit to make.
        output_suffix:     Suffix appended to document filename (e.g. "_edited").

    Returns:
        Path to the updated .docx file.

    Raises:
        FileNotFoundError: If the job artifacts are missing.
        ValueError: If the section heading is not found in the plan.
    """
    from app.config import settings
    from app.agents.pipeline import _write_section, _make_llm_json
    from app.tools.docx_builder import assemble_document

    # ── 1. Load existing artifacts ────────────────────────────────────────────
    plan = _load_artifact(job_id, "document_plan.json")
    sections: list[dict] = _load_artifact(job_id, "generated_sections.json")

    # ── 2. Find target section in plan ────────────────────────────────────────
    plan_sections = plan.get("sections", [])
    target_idx: int | None = None
    for i, ps in enumerate(plan_sections):
        if ps.get("heading", "").strip().lower() == section_heading.strip().lower():
            target_idx = i
            break

    if target_idx is None:
        available = [ps.get("heading", "") for ps in plan_sections]
        raise ValueError(
            f"Section '{section_heading}' not found in document plan. "
            f"Available headings: {available}"
        )

    section_plan = plan_sections[target_idx]
    doc_type = plan.get("doc_type", "BRD")

    # ── 3. Augment section plan with the edit instruction ─────────────────────
    # We prepend the edit instruction so the LLM knows exactly what to change.
    original_instructions = section_plan.get("content_instructions", "")
    augmented_plan = {
        **section_plan,
        "content_instructions": (
            f"[EDIT INSTRUCTION — FOLLOW PRECISELY]\n{edit_instruction}\n\n"
            f"[ORIGINAL SECTION GUIDANCE]\n{original_instructions}"
        ),
    }

    # ── 4. Regenerate only the target section ─────────────────────────────────
    logger.info(
        "[edit_document_section] Regenerating section '%s' for job %s",
        section_heading, job_id,
    )
    llm = _make_llm_json()
    rag_context = ""  # Edit doesn't use RAG — uses the instruction directly

    new_content = _write_section(
        llm,
        augmented_plan,
        rag_context,
        doc_type=doc_type,
        audience=plan.get("document_meta", {}).get("audience", ""),
        desired_outcome=plan.get("document_meta", {}).get("desired_outcome", ""),
    )

    # Force correct heading and metadata
    new_content["section_key"] = section_plan.get("section_key")
    new_content["render_style"] = section_plan.get("render_style", "body")
    new_content["level"] = section_plan.get("level", 1)
    new_content["section_heading"] = section_plan.get("heading", section_heading)
    if doc_type.strip().lower() in ("brd", "product note"):
        new_content["code_blocks"] = []

    # ── 5. Replace the section in the sections list ───────────────────────────
    updated_sections = list(sections)
    if target_idx < len(updated_sections):
        updated_sections[target_idx] = new_content
    else:
        # Section existed in plan but content was missing — append
        updated_sections.append(new_content)

    # ── 6. Persist updated sections artifact ─────────────────────────────────
    from app.plan_store import artifact_dir
    artifact_path = artifact_dir(job_id) / "generated_sections.json"
    artifact_path.write_text(
        json.dumps(updated_sections, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("[edit_document_section] Updated generated_sections.json for job %s", job_id)

    # ── 7. Re-assemble the document ───────────────────────────────────────────
    job_dir = Path(settings.output_dir) / job_id
    existing_doc = job_dir / "document.docx"
    output_path = str(job_dir / f"document{output_suffix}.docx")

    # Load diagram specs and generated diagrams from artifacts
    try:
        diagram_specs = _load_artifact(job_id, "document_plan.json").get("diagram_specs") or []
    except Exception:
        diagram_specs = []

    try:
        generated_diagrams = _load_artifact(job_id, "generated_diagrams.json") if (job_dir / "generated_diagrams.json").exists() else {}
    except Exception:
        generated_diagrams = {}

    final_path = assemble_document(
        plan,
        updated_sections,
        output_path,
        diagram_specs=plan.get("diagram_specs") or [],
        generated_diagrams=generated_diagrams,
    )

    logger.info("[edit_document_section] Re-assembled document: %s", final_path)
    return final_path


def edit_full_document(
    job_id: str,
    edit_instruction: str,
    output_suffix: str = "_edited",
) -> str:
    """Regenerate all planned sections using a document-wide edit instruction."""
    from app.config import settings
    from app.agents.pipeline import _write_section, _make_llm_json
    from app.tools.docx_builder import assemble_document
    from app.plan_store import artifact_dir

    plan = _load_artifact(job_id, "document_plan.json")
    sections: list[dict] = _load_artifact(job_id, "generated_sections.json")
    plan_sections = plan.get("sections", [])
    if not plan_sections:
        raise ValueError("Document plan does not contain any sections to edit.")

    llm = _make_llm_json()
    doc_type = plan.get("doc_type", "BRD")
    audience = plan.get("document_meta", {}).get("audience", "")
    desired_outcome = plan.get("document_meta", {}).get("desired_outcome", "")

    updated_sections: list[dict] = []
    for index, section_plan in enumerate(plan_sections):
        original_instructions = section_plan.get("content_instructions", "")
        augmented_plan = {
            **section_plan,
            "content_instructions": (
                f"[DOCUMENT-WIDE EDIT INSTRUCTION — APPLY CONSISTENTLY]\n{edit_instruction}\n\n"
                f"[ORIGINAL SECTION GUIDANCE]\n{original_instructions}"
            ),
        }

        logger.info(
            "[edit_full_document] Regenerating section '%s' (%s/%s) for job %s",
            section_plan.get("heading", f"Section {index + 1}"),
            index + 1,
            len(plan_sections),
            job_id,
        )

        new_content = _write_section(
            llm,
            augmented_plan,
            "",
            doc_type=doc_type,
            audience=audience,
            desired_outcome=desired_outcome,
        )
        new_content["section_key"] = section_plan.get("section_key")
        new_content["render_style"] = section_plan.get("render_style", "body")
        new_content["level"] = section_plan.get("level", 1)
        new_content["section_heading"] = section_plan.get("heading", f"Section {index + 1}")
        if doc_type.strip().lower() in ("brd", "product note"):
            new_content["code_blocks"] = []
        updated_sections.append(new_content)

    artifact_path = artifact_dir(job_id) / "generated_sections.json"
    artifact_path.write_text(
        json.dumps(updated_sections, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("[edit_full_document] Updated generated_sections.json for job %s", job_id)

    job_dir = Path(settings.output_dir) / job_id
    output_path = str(job_dir / f"document{output_suffix}.docx")

    try:
        generated_diagrams = _load_artifact(job_id, "generated_diagrams.json") if (job_dir / "generated_diagrams.json").exists() else {}
    except Exception:
        generated_diagrams = {}

    final_path = assemble_document(
        plan,
        updated_sections,
        output_path,
        diagram_specs=plan.get("diagram_specs") or [],
        generated_diagrams=generated_diagrams,
    )
    logger.info("[edit_full_document] Re-assembled document: %s", final_path)
    return final_path
