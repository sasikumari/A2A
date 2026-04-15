"""
Document Generation Pipeline — embedded directly in the product-builder backend.

Replaces all HTTP calls to the claudedocuer microservice with direct in-process
calls to the LangGraph pipeline. This eliminates:
  - Network timeouts (Gaps 8, 9)
  - Event-loop blocking (Gap 8)
  - Single-error full fallback (Gap 5)
  - Unbounded re-fetching of content (Gap 2)

Architecture:
  JOBS   { job_id  → job_state }    in-memory, thread-safe, TTL-evicted
  BUNDLES{ bundle_id → bundle_meta } in-memory, TTL-evicted

Public API:
  submit_bundle(prompt, feature, ...)  → bundle_id | None
  get_bundle(bundle_id, feature)       → bundle status dict
  get_job_content(job_id, doc_type, feature) → Document dict | None
  retry_doc(bundle_id, doc_type, prompt, feature) → new job_id | None
  run_edit(job_id, edit_instruction)   → new output_path (sync, thread-safe)
  cleanup_stale_jobs()                 → evicts jobs older than JOB_TTL_HOURS
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("docgen.pipeline")

# ---------------------------------------------------------------------------
# Resolve the embedded docgen root and make its packages importable.
# Walk upward until we find either:
#   1. a parent that contains docgen/app/main.py
#   2. a parent that directly contains app/main.py
# ---------------------------------------------------------------------------

def _resolve_docgen_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        embedded = parent / "docgen"
        if (embedded / "app" / "main.py").exists():
            return embedded
        if (parent / "app" / "main.py").exists():
            return parent
    raise RuntimeError(f"Could not resolve docgen root from {here}")


_DOCGEN_ROOT = _resolve_docgen_root()
if str(_DOCGEN_ROOT) not in sys.path:
    sys.path.insert(0, str(_DOCGEN_ROOT))

# Set absolute env-var defaults BEFORE importing app.config so pydantic Settings
# resolves paths relative to the claudedocuer root, not the backend cwd.
os.environ.setdefault("OUTPUT_DIR",      str(_DOCGEN_ROOT / "outputs"))
os.environ.setdefault("VECTORSTORE_DIR", str(_DOCGEN_ROOT / "vectorstore"))
os.environ.setdefault("UPLOAD_DIR",      str(_DOCGEN_ROOT / "uploads"))

# ---------------------------------------------------------------------------
# Lazy pipeline import — graceful when claudedocuer deps are missing
# ---------------------------------------------------------------------------

_pipeline_loaded: bool = False
_run_pipeline = None
_get_pipeline_fn = None
_edit_full_document_fn = None
_edit_section_fn = None


def _ensure_pipeline() -> bool:
    global _pipeline_loaded, _run_pipeline, _get_pipeline_fn, _edit_full_document_fn, _edit_section_fn
    if _pipeline_loaded:
        return _run_pipeline is not None
    _pipeline_loaded = True
    try:
        from app.agents.pipeline import get_pipeline as _gp, run_pipeline as _rp
        from app.tools.document_editor import (
            edit_full_document as _efd,
            edit_document_section as _eds,
        )
        _run_pipeline = _rp
        _get_pipeline_fn = _gp
        _edit_full_document_fn = _efd
        _edit_section_fn = _eds
        logger.info("[document_pipeline] LangGraph pipeline loaded from %s", _DOCGEN_ROOT)
        return True
    except Exception as exc:
        logger.warning(
            "[document_pipeline] Pipeline import failed — document generation unavailable. "
            "Error: %s",
            exc,
        )
        return False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JOB_TTL_HOURS = 4

_BUNDLE_DOC_TYPES = ["BRD", "TSD", "Product Note", "Circular"]

DOC_TYPE_META: dict[str, dict] = {
    "BRD": {
        "id": "product-doc",
        "icon": "FileText",
        "title_prefix": "Business Requirements Document",
    },
    "TSD": {
        "id": "test-cases",
        "icon": "TestTube2",
        "title_prefix": "Technical Specification Document",
    },
    "Product Note": {
        "id": "product-note",
        "icon": "FileText",
        "title_prefix": "Product Note",
    },
    "Circular": {
        "id": "circular-draft",
        "icon": "ScrollText",
        "title_prefix": "Regulatory Circular",
    },
}

# Maps pipeline status strings → 0-100 progress and human-readable step label
STATUS_PROGRESS: dict[str, int] = {
    "pending": 0,
    "retrieving": 10,
    "planning": 30,
    "generating_diagrams": 50,
    "writing": 70,
    "reviewing": 82,
    "assembling": 90,
    "completed": 100,
    "failed": 0,
    "FAILED": 0,
}
STATUS_STEP: dict[str, str] = {
    "pending": "Queued",
    "retrieving": "Retrieving UPI knowledge base context",
    "planning": "Planning document structure",
    "generating_diagrams": "Generating architecture diagrams",
    "writing": "Writing section content",
    "reviewing": "Reviewing document quality",
    "assembling": "Assembling final DOCX",
    "completed": "Document ready",
    "failed": "Generation failed",
    "FAILED": "Generation failed",
}

# Normalise any status string the pipeline returns into frontend-expected values
_TERMINAL_STATUSES = {"completed", "failed"}
_RUNNING_STATUSES  = {"retrieving", "planning", "generating_diagrams", "writing", "reviewing", "assembling"}


def _normalise_status(raw: str) -> str:
    """Map raw pipeline status → one of {pending, running, completed, failed}."""
    s = (raw or "pending").lower()
    if s == "completed":
        return "completed"
    if s in {"failed", "error"}:
        return "failed"
    if s in {"pending"}:
        return "pending"
    return "running"  # retrieving / planning / writing / reviewing / assembling


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------

JOBS: dict[str, dict]    = {}
BUNDLES: dict[str, dict] = {}
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Pipeline background runner
# ---------------------------------------------------------------------------

def _update_job_from_state(job_id: str, state: dict) -> None:
    raw = state.get("status", "pending")
    with _lock:
        if job_id not in JOBS:
            return
        JOBS[job_id]["status"]       = raw
        JOBS[job_id]["progress"]     = STATUS_PROGRESS.get(raw, JOBS[job_id].get("progress", 0))
        JOBS[job_id]["current_step"] = STATUS_STEP.get(raw, raw)
        JOBS[job_id]["error"]        = state.get("error")
        JOBS[job_id]["output_path"]  = state.get("output_path")


def _run_pipeline_bg(job_id: str, initial_state: dict) -> None:
    """Daemon thread target: run one document pipeline job to completion."""
    doc_type = initial_state.get("doc_type", "?")
    logger.info("[pipeline_bg] START job_id=%s doc_type=%s", job_id, doc_type)
    t0 = time.time()
    try:
        with _lock:
            if job_id in JOBS:
                JOBS[job_id]["status"]       = "retrieving"
                JOBS[job_id]["progress"]     = STATUS_PROGRESS["retrieving"]
                JOBS[job_id]["current_step"] = STATUS_STEP["retrieving"]
        final_state = initial_state
        if _get_pipeline_fn is not None:
            pipeline = _get_pipeline_fn()
            for state_update in pipeline.stream(initial_state, stream_mode="values"):
                if isinstance(state_update, dict):
                    final_state = state_update
                    _update_job_from_state(job_id, state_update)
        else:
            final_state = _run_pipeline(initial_state)
            _update_job_from_state(job_id, final_state)
        logger.info(
            "[pipeline_bg] DONE  job_id=%s doc_type=%s status=%s elapsed=%.1fs",
            job_id, doc_type, final_state.get("status", "?"), time.time() - t0,
        )
    except Exception as exc:
        logger.error(
            "[pipeline_bg] FAIL  job_id=%s doc_type=%s elapsed=%.1fs: %s",
            job_id, doc_type, time.time() - t0, exc, exc_info=True,
        )
        with _lock:
            if job_id in JOBS:
                JOBS[job_id]["status"]       = "failed"
                JOBS[job_id]["error"]        = str(exc)
                JOBS[job_id]["progress"]     = 0
                JOBS[job_id]["current_step"] = "Generation failed"


def _build_initial_state(
    job_id: str,
    bundle_id: str,
    doc_type: str,
    prompt: str,
    feature: str,
    organization_name: str,
    title: str,
) -> dict:
    """Construct the LangGraph initial state dict for one document job."""
    today = datetime.utcnow().strftime("%d %B %Y")
    return {
        "job_id":        job_id,
        "prompt":        prompt,
        "doc_type":      doc_type,
        "document_title": title,
        "version_number": "1.0",
        "classification": "Internal",
        # Gap 1 FIX: always use the UPI knowledge collection, not the empty "default"
        "collection_name": "upi_knowledge",
        "reference_structure": None,
        "use_rag":       True,
        "include_diagrams": doc_type != "Circular",
        "audience":      "NPCI Product Management, Compliance, Engineering",
        "desired_outcome": f"Production-grade NPCI {doc_type} for {feature}",
        "format_constraints": None,
        "organization_name": organization_name,
        "reference_code": None,
        "issue_date":    today,
        "recipient_line": "All Member Banks, PSPs, TPAPs",
        "subject_line":  f"{feature} — {doc_type}",
        "signatory_name": "Chief Product Officer",
        "signatory_title": "CPO",
        "signatory_department": "Product Management",
        "additional_context": None,
        "session_id":    bundle_id,
        "rag_context":   "",
        "rag_chunks":    [],
        "document_plan": None,
        "diagram_specs": [],
        "generated_diagrams": {},
        "generated_sections": [],
        "output_path":   None,
        "status":        "pending",
        "error":         None,
    }


# ---------------------------------------------------------------------------
# Public: submit_bundle
# ---------------------------------------------------------------------------

def submit_bundle(
    prompt: str,
    feature: str,
    organization_name: str = "NPCI",
    brd_title: Optional[str] = None,
    tsd_title: Optional[str] = None,
    product_note_title: Optional[str] = None,
    circular_title: Optional[str] = None,
    doc_types: Optional[list[str]] = None,   # None = all four
) -> Optional[str]:
    """
    Spawn one daemon thread per doc_type and return a bundle_id immediately.
    Returns None if the pipeline could not be loaded.
    """
    if not _ensure_pipeline():
        return None

    cleanup_stale_jobs()

    types_to_generate = doc_types or _BUNDLE_DOC_TYPES
    bundle_id = str(uuid.uuid4())

    title_overrides = {
        "BRD":          brd_title          or f"BRD — {feature}",
        "TSD":          tsd_title          or f"TSD — {feature}",
        "Product Note": product_note_title or f"Product Note — {feature}",
        "Circular":     circular_title     or f"Circular — {feature}",
    }

    job_ids: dict[str, str] = {}
    for doc_type in types_to_generate:
        if doc_type not in _BUNDLE_DOC_TYPES:
            logger.warning("[submit_bundle] Unknown doc_type '%s' — skipping", doc_type)
            continue

        job_id = str(uuid.uuid4())
        job_ids[doc_type] = job_id

        with _lock:
            JOBS[job_id] = {
                "status":         "pending",
                "progress":       0,
                "current_step":   "Queued",
                "error":          None,
                "output_path":    None,
                "doc_type":       doc_type,
                "bundle_id":      bundle_id,
                "submitted_at":   datetime.utcnow().isoformat(),
                "_content_cache": None,   # Gap 2: populated once, then reused
            }

        initial_state = _build_initial_state(
            job_id=job_id,
            bundle_id=bundle_id,
            doc_type=doc_type,
            prompt=prompt,
            feature=feature,
            organization_name=organization_name,
            title=title_overrides[doc_type],
        )

        t = threading.Thread(
            target=_run_pipeline_bg,
            args=(job_id, initial_state),
            daemon=True,
            name=f"docgen-{doc_type[:3].lower()}-{job_id[:6]}",
        )
        t.start()
        logger.info("[submit_bundle] Spawned thread for doc_type=%s job_id=%s", doc_type, job_id)

    with _lock:
        BUNDLES[bundle_id] = {
            "job_ids":      job_ids,
            "feature":      feature,
            "submitted_at": datetime.utcnow().isoformat(),
        }

    logger.info(
        "[submit_bundle] bundle_id=%s — %d jobs started for feature='%s'",
        bundle_id, len(job_ids), feature,
    )
    return bundle_id


# ---------------------------------------------------------------------------
# Public: get_bundle
# ---------------------------------------------------------------------------

def get_bundle(bundle_id: str, feature: str) -> dict:
    """
    Return the current status of all jobs in the bundle.
    Gap 2 FIX: completed doc content is fetched from disk exactly once and then
    served from an in-memory cache for all subsequent calls.
    Raises KeyError if bundle not found.
    """
    with _lock:
        if bundle_id not in BUNDLES:
            raise KeyError(f"Bundle {bundle_id} not found")
        bundle   = BUNDLES[bundle_id]
        job_ids  = dict(bundle["job_ids"])  # snapshot

    jobs_detail: list[dict] = []
    completed_docs: list[dict] = []

    for doc_type in _BUNDLE_DOC_TYPES:
        job_id = job_ids.get(doc_type)

        # Doc type not in this bundle (e.g. single-type retry)
        if not job_id:
            jobs_detail.append(_placeholder_job(doc_type, feature))
            continue

        with _lock:
            job_snap = dict(JOBS.get(job_id, {}))  # snapshot under lock

        if not job_snap:
            jobs_detail.append(_placeholder_job(doc_type, feature))
            continue

        raw_status = job_snap.get("status", "pending")
        norm_status = _normalise_status(raw_status)
        progress    = STATUS_PROGRESS.get(raw_status, job_snap.get("progress", 0))
        current_step = job_snap.get("current_step") or STATUS_STEP.get(raw_status, raw_status)

        meta = DOC_TYPE_META.get(doc_type, {
            "id":           doc_type.lower().replace(" ", "-"),
            "icon":         "FileText",
            "title_prefix": doc_type,
        })

        job_detail = {
            "doc_type":     doc_type,
            "job_id":       job_id,
            "status":       norm_status,
            "progress":     progress,
            "current_step": current_step,
            "error":        job_snap.get("error"),
            "document": {
                "id":             meta["id"],
                "title":          f"{meta['title_prefix']} — {feature}",
                "icon":           meta["icon"],
                "content":        "",
                "approved":       False,
                "_status":        norm_status if norm_status in {"completed", "failed"} else "generating",
                "_progress":      progress,
                "_doc_type":      doc_type,
                "_docgen_job_id": job_id,
            },
        }
        jobs_detail.append(job_detail)

        # Fetch content once for completed jobs
        if norm_status == "completed":
            doc = _get_or_fetch_content(job_id, doc_type, feature)
            if doc:
                completed_docs.append(doc)
                job_detail["document"] = doc

    statuses = [j["status"] for j in jobs_detail]
    if all(s == "completed" for s in statuses):
        overall = "completed"
    elif all(s in _TERMINAL_STATUSES for s in statuses):
        overall = "partial"
    elif any(s in _TERMINAL_STATUSES for s in statuses):
        overall = "running"
    else:
        overall = "running" if any(s != "pending" for s in statuses) else "pending"

    return {
        "bundle_id":      bundle_id,
        "overall_status": overall,
        "jobs":           jobs_detail,
        "documents":      [d for d in completed_docs if d],
    }


# ---------------------------------------------------------------------------
# Content fetching with cache (Gap 2)
# ---------------------------------------------------------------------------

def _get_or_fetch_content(job_id: str, doc_type: str, feature: str, force_refresh: bool = False) -> Optional[dict]:
    """Return cached Document dict, or read from disk artifacts and cache."""
    with _lock:
        if force_refresh and job_id in JOBS:
            JOBS[job_id]["_content_cache"] = None
        cached = JOBS.get(job_id, {}).get("_content_cache")
    if cached is not None and not force_refresh:
        return cached

    doc = _build_document_from_artifacts(job_id, doc_type, feature)
    if doc is not None:
        with _lock:
            if job_id in JOBS:
                JOBS[job_id]["_content_cache"] = doc
    return doc


def _build_document_from_artifacts(job_id: str, doc_type: str, feature: str) -> Optional[dict]:
    """Read generated_sections.json + document_plan.json → Document dict.

    Also embeds _bundle_id (from JOBS if available) so the download endpoint
    can directly construct the session-scoped DOCX path without scanning.
    """
    try:
        from app.config import settings
        job_dir       = Path(settings.output_dir) / job_id
        sections_file = job_dir / "generated_sections.json"
        plan_file     = job_dir / "document_plan.json"

        if not sections_file.exists():
            logger.warning("[build_doc] sections_file missing job_id=%s", job_id)
            return None

        sections = json.loads(sections_file.read_text(encoding="utf-8"))
        plan     = json.loads(plan_file.read_text(encoding="utf-8")) if plan_file.exists() else {}
        markdown = _sections_to_markdown(sections, plan)
    except Exception as exc:
        logger.error("[build_doc] artifact read failed job_id=%s: %s", job_id, exc)
        markdown = f"# {doc_type} — {feature}\n\n*Content could not be rendered.*"

    # Grab bundle_id from JOBS if still present (used for direct session path lookup)
    with _lock:
        bundle_id = JOBS.get(job_id, {}).get("bundle_id")

    meta = DOC_TYPE_META.get(doc_type, {
        "id":           doc_type.lower().replace(" ", "-"),
        "icon":         "FileText",
        "title_prefix": doc_type,
    })
    doc = {
        "id":             meta["id"],
        "title":          f"{meta['title_prefix']} — {feature}",
        "icon":           meta["icon"],
        "content":        markdown,
        "approved":       False,
        "_status":        "completed",
        "_progress":      100,
        "_doc_type":      doc_type,
        "_docgen_job_id": job_id,
    }
    if bundle_id:
        doc["_bundle_id"] = bundle_id
    return doc


def _sections_to_markdown(sections: list, plan: dict) -> str:
    """Convert generated_sections.json list to a markdown string."""
    lines: list[str] = []

    title    = plan.get("title", "")
    subtitle = plan.get("subtitle", "")
    doc_type = plan.get("doc_type", "")
    meta     = plan.get("document_meta", {}) or {}

    # Document-facing meta keys only (excludes internal pipeline fields)
    _DOC_META_KEYS = {
        "organization_name", "reference_code", "issue_date", "recipient_line",
        "subject_line", "version_number", "classification",
    }
    # Keys whose value is a list/dict — skip them from inline rendering
    _SKIP_VALUE_TYPES = (list, dict)

    # Subtitle guard: the LLM planner sometimes puts the full prompt in this
    # field.  Drop it if it looks like a generation instruction.
    _PROMPT_PREFIXES = (
        "generate a comprehensive",
        "generate comprehensive",
        "create a comprehensive",
        "write a comprehensive",
    )
    _clean_subtitle = (subtitle or "").strip()
    _show_subtitle = (
        _clean_subtitle
        and not any(_clean_subtitle.lower().startswith(p) for p in _PROMPT_PREFIXES)
        and len(_clean_subtitle) < 200  # avoid multi-line prompt bleed
    )

    if title:
        lines.append(f"# {title}")
    if _show_subtitle:
        lines.append(f"*{_clean_subtitle}*")
    if doc_type:
        lines.append(f"**Document Type:** {doc_type}")

    # Render only the document-facing meta fields
    for k in _DOC_META_KEYS:
        v = meta.get(k)
        if v and not isinstance(v, _SKIP_VALUE_TYPES):
            label = k.replace("_", " ").title()
            lines.append(f"**{label}:** {v}")

    # Revision history as a compact table if present
    rev_history = meta.get("revision_history")
    if rev_history and isinstance(rev_history, list) and rev_history:
        lines += ["", "**Revision History:**", ""]
        lines.append("| Version | Date | Changed By | Remarks |")
        lines.append("| --- | --- | --- | --- |")
        for row in rev_history:
            if isinstance(row, dict):
                ver  = row.get("version_no") or row.get("version", "")
                date = row.get("date_of_change", "")
                by   = row.get("changed_by", "")
                rem  = row.get("remarks", "")
                lines.append(f"| {ver} | {date} | {by} | {rem} |")

    if lines:
        lines += ["", "---", ""]

    # Circular-specific render_styles that should NOT show a heading
    _CIRCULAR_HEADING_SKIP = {
        "circular_reference", "circular_addressee", "circular_subject",
        "circular_dissemination", "circular_signature",
    }

    for section in sections:
        heading      = section.get("section_heading", "")
        level        = section.get("level", 1)
        render_style = section.get("render_style", "body")
        prefix       = "#" * min(level + 1, 4)

        # For circular structural blocks, suppress the internal heading label
        # (e.g. "Letterhead & Reference Block") and just show the content.
        show_heading = heading and render_style not in _CIRCULAR_HEADING_SKIP
        if show_heading:
            lines += [f"{prefix} {heading}", ""]

        if render_style == "cover":
            for p in section.get("paragraphs", []):
                if p and p.strip():
                    lines.append(p.strip())
            lines.append("")
            continue

        for p in section.get("paragraphs", []):
            if p and p.strip():
                lines += [p.strip(), ""]

        bullets = section.get("bullet_points", [])
        if bullets:
            for b in bullets:
                if b:
                    lines.append(f"- {b}")
            lines.append("")

        numbered = section.get("numbered_items", [])
        if numbered:
            for i, item in enumerate(numbered, 1):
                lines.append(f"{i}. {item}")
            lines.append("")

        table   = section.get("table_data") or {}
        headers = table.get("headers", [])
        rows    = table.get("rows", [])
        if headers and rows:
            lines.append("| " + " | ".join(str(h) for h in headers) + " |")
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in rows:
                lines.append("| " + " | ".join(str(c) for c in row) + " |")
            lines.append("")

        for code in section.get("code_blocks", []):
            if code and code.strip():
                lines += ["```", code.strip(), "```", ""]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public: get_job_content
# ---------------------------------------------------------------------------

def get_job_content(job_id: str, doc_type: str, feature: str, force_refresh: bool = False) -> Optional[dict]:
    """Return the Document dict for a single completed job.

    Does NOT bail when JOBS is empty (server restart / TTL eviction).
    Always attempts disk read so the correct pipeline-generated content
    is served even after a server restart.
    """
    # Attempt disk read regardless of whether JOBS has this entry.
    # _get_or_fetch_content handles its own cache/force_refresh logic.
    return _get_or_fetch_content(job_id, doc_type, feature, force_refresh=force_refresh)


def get_job_output_path(job_id: str, bundle_id: Optional[str] = None, doc_type: Optional[str] = None) -> Optional[str]:
    """Return the DOCX output path for a job.

    Resolution order:
      L1. JOBS[job_id]["output_path"]                              (set during streaming)
      L2. outputs/sessions/{bundle_id}/{doc_type}_{job_id[:8]}.docx (direct session path)
      L3. outputs/{job_id}/document_edited.docx                    (edited job-scoped)
      L4. outputs/{job_id}/document.docx                           (job-scoped)
      L5. outputs/sessions/*/  glob scan by job_id prefix          (full scan)
    """
    with _lock:
        job_entry = JOBS.get(job_id, {})
        stored    = job_entry.get("output_path")
        # Use bundle_id / doc_type from JOBS if not supplied by caller
        _bundle   = bundle_id or job_entry.get("bundle_id")
        _dtype    = doc_type  or job_entry.get("doc_type")

    # L1 — in-memory output_path (set by pipeline streaming)
    if stored and Path(stored).exists():
        return stored

    # L2 — direct session path using known bundle_id + doc_type (fastest disk path)
    if _bundle and _dtype:
        doc_type_slug = _dtype.lower().replace(" ", "_")
        session_candidate = _DOCGEN_ROOT / "outputs" / "sessions" / _bundle / f"{doc_type_slug}_{job_id[:8]}.docx"
        if session_candidate.exists():
            logger.info("[get_job_output_path] direct session path resolved %s → %s", job_id, session_candidate)
            return str(session_candidate)

    # L3/L4 — job-scoped output directory
    job_dir = _DOCGEN_ROOT / "outputs" / job_id
    for name in ("document_edited.docx", "document.docx"):
        candidate = job_dir / name
        if candidate.exists():
            logger.info("[get_job_output_path] job-dir fallback resolved %s → %s", job_id, candidate)
            return str(candidate)

    # L5 — full session scan by job_id prefix (server-restart / unknown bundle)
    sessions_dir = _DOCGEN_ROOT / "outputs" / "sessions"
    if sessions_dir.is_dir():
        prefix = job_id[:8]
        for bundle_dir in sessions_dir.iterdir():
            if not bundle_dir.is_dir():
                continue
            matches = list(bundle_dir.glob(f"*{prefix}*.docx"))
            if matches:
                edited = [m for m in matches if "edited" in m.name]
                chosen = (edited or matches)[0]
                logger.info("[get_job_output_path] session scan resolved %s → %s", job_id, chosen)
                return str(chosen)

    return None


# ---------------------------------------------------------------------------
# Public: retry_doc
# ---------------------------------------------------------------------------

def retry_doc(bundle_id: str, doc_type: str, prompt: str, feature: str) -> Optional[str]:
    """
    Spawn a fresh pipeline thread for a single failed doc in an existing bundle.
    Replaces the failed job_id in the bundle. Returns new job_id or None.
    Gap 6 FIX: enables per-doc retry without regenerating all 4 documents.
    """
    if not _ensure_pipeline():
        return None

    with _lock:
        if bundle_id not in BUNDLES:
            return None
        bundle = BUNDLES[bundle_id]

    new_job_id = str(uuid.uuid4())
    title = DOC_TYPE_META.get(doc_type, {}).get("title_prefix", doc_type) + f" — {feature}"

    with _lock:
        JOBS[new_job_id] = {
            "status":         "pending",
            "progress":       0,
            "current_step":   "Queued",
            "error":          None,
            "output_path":    None,
            "doc_type":       doc_type,
            "bundle_id":      bundle_id,
            "submitted_at":   datetime.utcnow().isoformat(),
            "_content_cache": None,
        }
        BUNDLES[bundle_id]["job_ids"][doc_type] = new_job_id

    initial_state = _build_initial_state(
        job_id=new_job_id,
        bundle_id=bundle_id,
        doc_type=doc_type,
        prompt=prompt,
        feature=feature,
        organization_name=bundle.get("organization_name", "NPCI"),
        title=title,
    )

    t = threading.Thread(
        target=_run_pipeline_bg,
        args=(new_job_id, initial_state),
        daemon=True,
        name=f"docgen-retry-{doc_type[:3].lower()}-{new_job_id[:6]}",
    )
    t.start()
    logger.info("[retry_doc] bundle_id=%s doc_type=%s new_job_id=%s", bundle_id, doc_type, new_job_id)
    return new_job_id


# ---------------------------------------------------------------------------
# Public: run_edit
# ---------------------------------------------------------------------------

def run_edit(job_id: str, edit_instruction: str) -> str:
    """
    Run a full-document edit synchronously and return the new output path.

    Gap 8 FIX: Called from a sync FastAPI endpoint — runs in FastAPI's thread pool,
    never blocks the asyncio event loop (unlike claudedocuer's async def endpoint).

    Gap 9 FIX: No HTTP timeout. The edit runs until completion regardless of duration.
    The content cache is cleared so the next fetch rebuilds from the updated artifact.
    """
    if not _ensure_pipeline():
        raise RuntimeError("Pipeline not available for editing")

    with _lock:
        job = dict(JOBS.get(job_id, {}))
    if not job:
        raise KeyError(f"Job {job_id} not found")
    if job.get("status") != "completed":
        raise ValueError(
            f"Job {job_id} is not completed (status={job.get('status')}). "
            "Cannot edit a document that is still generating or has failed."
        )

    logger.info("[run_edit] START job_id=%s instruction_len=%d", job_id, len(edit_instruction))
    t0 = time.time()
    new_path = _edit_full_document_fn(job_id, edit_instruction)
    elapsed = time.time() - t0
    logger.info("[run_edit] DONE  job_id=%s elapsed=%.1fs path=%s", job_id, elapsed, new_path)

    # Clear cache and update output_path so next fetch reads the edited file
    with _lock:
        if job_id in JOBS:
            JOBS[job_id]["output_path"]    = new_path
            JOBS[job_id]["_content_cache"] = None

    return new_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _placeholder_job(doc_type: str, feature: str) -> dict:
    meta = DOC_TYPE_META.get(doc_type, {
        "id":           doc_type.lower().replace(" ", "-"),
        "icon":         "FileText",
        "title_prefix": doc_type,
    })
    return {
        "doc_type":     doc_type,
        "job_id":       None,
        "status":       "pending",
        "progress":     0,
        "current_step": "Queued",
        "error":        None,
        "document": {
            "id":             meta["id"],
            "title":          f"{meta['title_prefix']} — {feature}",
            "icon":           meta["icon"],
            "content":        "",
            "approved":       False,
            "_status":        "generating",
            "_progress":      0,
            "_doc_type":      doc_type,
            "_docgen_job_id": None,
        },
    }


# ---------------------------------------------------------------------------
# TTL eviction — Gap 17
# ---------------------------------------------------------------------------

def cleanup_stale_jobs() -> None:
    """Evict completed/failed jobs and expired bundles older than JOB_TTL_HOURS."""
    cutoff = datetime.utcnow() - timedelta(hours=JOB_TTL_HOURS)
    removed_jobs = removed_bundles = 0

    with _lock:
        stale_jobs = [
            jid for jid, j in JOBS.items()
            if j.get("status") in {"completed", "failed", "FAILED"}
            and _parse_iso(j.get("submitted_at")) < cutoff
        ]
        for jid in stale_jobs:
            del JOBS[jid]
            removed_jobs += 1

        stale_bundles = [
            bid for bid, b in BUNDLES.items()
            if _parse_iso(b.get("submitted_at")) < cutoff
        ]
        for bid in stale_bundles:
            del BUNDLES[bid]
            removed_bundles += 1

    if removed_jobs or removed_bundles:
        logger.info(
            "[cleanup] Evicted %d stale jobs, %d stale bundles (TTL=%dh)",
            removed_jobs, removed_bundles, JOB_TTL_HOURS,
        )


def _parse_iso(dt_str: Optional[str]) -> datetime:
    if not dt_str:
        return datetime.min
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        return datetime.min


# ---------------------------------------------------------------------------
# Bundle metadata helpers (used by document_agent for retry/prompt storage)
# ---------------------------------------------------------------------------

def get_bundle_prompt(bundle_id: str) -> Optional[str]:
    """Return the original prompt for a bundle (needed for per-doc retry)."""
    with _lock:
        return BUNDLES.get(bundle_id, {}).get("prompt")


def store_bundle_prompt(bundle_id: str, prompt: str) -> None:
    """Store the prompt alongside the bundle for retry use."""
    with _lock:
        if bundle_id in BUNDLES:
            BUNDLES[bundle_id]["prompt"] = prompt
