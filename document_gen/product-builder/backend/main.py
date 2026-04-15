"""
Product Builder Backend — FastAPI server
Connects to the vLLM model at http://183.82.7.228:9535
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("product_builder")

from agents.canvas_agent import CanvasAgent
from agents.followup_agent import FollowupAgent
from agents.document_agent import DocumentAgent
from agents.prototype_agent import PrototypeAgent
from agents.execution_agent import ExecutionAgent
from agents.test_agent import TestAgent
from agents.certification_agent import CertificationAgent
from agents.clarify_agent import evaluate as clarify_evaluate
from agents.research_agent import build_thinking_steps_from_research, search as kb_search
from utils.docx_generator import create_formal_docx
from utils.ppt_generator import create_ppt
"""
Main entry point for the Titan Product Builder Backend.
Orchestrates the agentic workflow across different phases of the product lifestyle.
"""
import os
from fastapi.responses import FileResponse
import tempfile

from registry_api import router as registry_router

app = FastAPI(title="Product Builder API", version="1.0.0")
app.include_router(registry_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

canvas_agent = CanvasAgent()
followup_agent = FollowupAgent()
document_agent = DocumentAgent()
prototype_agent = PrototypeAgent()
execution_agent = ExecutionAgent()
test_agent = TestAgent()
certification_agent = CertificationAgent()


# ─── Request Models ────────────────────────────────────────────────────────────

class ClarificationQA(BaseModel):
    question: str
    answer: str


class GenerateCanvasRequest(BaseModel):
    prompt: str
    feature_name: str
    clarification_qa: Optional[list] = None


class FollowupRequest(BaseModel):
    user_text: str
    canvas: dict
    feature_name: Optional[str] = ""


class DocumentsRequest(BaseModel):
    canvas: dict
    feedback: Optional[str] = None


class DocumentStatusRequest(BaseModel):
    bundle_id: str
    feature_name: str


class DocumentEditRequest(BaseModel):
    job_id: str
    edit_instruction: str
    feature_name: str
    doc_type: str


class DocumentRetryRequest(BaseModel):
    canvas: dict
    bundle_id: str
    doc_type: str


class PrototypeRequest(BaseModel):
    canvas: dict
    feedback: Optional[str] = None


class ExecutionRequest(BaseModel):
    canvas: dict
    feedback: Optional[str] = ""
    messages: Optional[list] = []


class VerifyTestRequest(BaseModel):
    prompt: str
    canvas: dict

class CertifyRequest(BaseModel):
    featureName: str
    canvas: dict
    changeManifest: dict
    testResults: list


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "product-builder-backend"}


@app.post("/api/canvas/generate")
def generate_canvas(req: GenerateCanvasRequest):
    """
    Generate a full 10-section Product Build Canvas using the AI agents.
    The response includes the canvas data and thinking steps extracted from the LLM.
    """
    if not req.prompt.strip():
        raise HTTPException(400, "prompt is required")
    if not req.feature_name.strip():
        req.feature_name = req.prompt.split()[:4]
        req.feature_name = " ".join(req.feature_name) if isinstance(req.feature_name, list) else req.feature_name

    t0 = time.time()
    result = canvas_agent.generate(req.prompt, req.feature_name, req.clarification_qa or [])
    elapsed = time.time() - t0

    # Build thinking steps from research findings + LLM thinking
    research = result.get("research", {})
    if research.get("documents"):
        thinking_steps = build_thinking_steps_from_research(
            research, req.feature_name, result.get("thinking", "")
        )
    else:
        thinking_steps = _build_thinking_steps(result.get("thinking", ""), req.feature_name)

    return {
        "canvas": result["canvas"],
        "thinking_steps": thinking_steps,
        "research": research,
        "elapsed_ms": int(elapsed * 1000),
    }


class ClarifyRequest(BaseModel):
    prompt: str
    feature_name: str


@app.post("/api/canvas/clarify")
def canvas_clarify(req: ClarifyRequest):
    """Evaluate prompt completeness and return clarification questions if needed."""
    if not req.feature_name.strip() or not req.prompt.strip():
        raise HTTPException(400, "feature_name and prompt are required")
    logger.info("[canvas/clarify] feature='%s' prompt_len=%d", req.feature_name, len(req.prompt))
    try:
        result = clarify_evaluate(req.prompt, req.feature_name)
        logger.info(
            "[canvas/clarify] feature='%s' confident=%s questions=%d",
            req.feature_name, result.get("confident"), len(result.get("questions", [])),
        )
        return result
    except Exception as exc:
        logger.error("[canvas/clarify] error for feature='%s': %s", req.feature_name, exc, exc_info=True)
        raise HTTPException(500, f"Clarification failed: {exc}")


class ResearchRequest(BaseModel):
    query: str
    feature_name: Optional[str] = ""


@app.post("/api/research/search")
def research_search(req: ResearchRequest):
    """Search the RBI/NPCI document knowledge base."""
    if not req.query.strip():
        raise HTTPException(400, "query is required")
    docs = kb_search(req.query, req.feature_name or "", top_n=8)
    return {"results": docs, "total": len(docs)}


@app.post("/api/canvas/followup")
def canvas_followup(req: FollowupRequest):
    """Handle follow-up messages for canvas refinement."""
    if not req.user_text.strip():
        raise HTTPException(400, "user_text is required")
    if not req.canvas:
        raise HTTPException(400, "canvas is required")

    result = followup_agent.respond(req.user_text, req.canvas)
    return result


@app.post("/api/documents/generate")
def generate_documents(req: DocumentsRequest):
    """Submit document generation and return tracking metadata immediately."""
    if not req.canvas:
        raise HTTPException(400, "canvas is required")

    feature = req.canvas.get("featureName", "unknown")
    logger.info("[documents/generate] Submitting bundle for feature='%s'", feature)
    t0 = time.time()
    result = document_agent.start_generation(req.canvas, req.feedback)
    elapsed_ms = int((time.time() - t0) * 1000)
    status = result.get("status", "unknown")
    bundle_id = result.get("bundle_id", "N/A")
    logger.info(
        "[documents/generate] feature='%s' → status=%s, bundle_id=%s, elapsed=%dms",
        feature, status, bundle_id, elapsed_ms,
    )
    if status == "fallback":
        logger.warning(
            "[documents/generate] claudedocuer unreachable — serving local fallback documents for '%s'",
            feature,
        )
    return result


@app.get("/api/documents/status/{bundle_id}")
def document_generation_status(bundle_id: str, feature_name: str):
    """Return live status for a submitted document bundle."""
    try:
        data = document_agent.get_bundle_status(bundle_id, feature_name)
        overall = data.get("overall_status", "?")
        jobs = data.get("jobs", [])
        completed = sum(1 for j in jobs if j.get("status") == "completed")
        logger.info(
            "[documents/status] bundle_id=%s feature='%s' overall=%s docs=%d/%d",
            bundle_id, feature_name, overall, completed, len(jobs),
        )
        return data
    except Exception as exc:
        logger.error("[documents/status] bundle_id=%s error: %s", bundle_id, exc)
        raise HTTPException(502, f"Failed to fetch bundle status: {exc}")


@app.get("/api/documents/content/{job_id}")
def document_content(job_id: str, doc_type: str, feature_name: str, force_refresh: bool = False):
    """Fetch the latest markdown content for one completed document."""
    try:
        document = document_agent.fetch_document(job_id, doc_type, feature_name, force_refresh=force_refresh)
    except Exception as exc:
        raise HTTPException(502, f"Failed to fetch document content: {exc}")

    if not document:
        raise HTTPException(404, "Document content not available")
    return {"document": document}


@app.post("/api/documents/edit")
def edit_document(req: DocumentEditRequest):
    """Apply a document-wide edit instruction via claudedocuer and return the refreshed document."""
    logger.info(
        "[documents/edit] job_id=%s doc_type=%s feature='%s' instruction_len=%d",
        req.job_id, req.doc_type, req.feature_name, len(req.edit_instruction),
    )
    try:
        document = document_agent.edit_document(
            job_id=req.job_id,
            edit_instruction=req.edit_instruction,
            feature=req.feature_name,
            doc_type=req.doc_type,
        )
    except Exception as exc:
        logger.error("[documents/edit] job_id=%s error: %s", req.job_id, exc)
        raise HTTPException(502, f"Failed to edit document: {exc}")

    if not document:
        raise HTTPException(500, "Edit completed but refreshed document could not be loaded")
    logger.info("[documents/edit] job_id=%s — edit applied successfully", req.job_id)
    return {"document": document}


@app.post("/api/documents/retry")
def retry_document(req: DocumentRetryRequest):
    """
    Retry generation for a single failed document without regenerating the whole bundle.
    Gap 6 FIX: preserves the 3 already-completed docs.
    """
    feature = req.canvas.get("featureName", "unknown")
    logger.info(
        "[documents/retry] bundle_id=%s doc_type=%s feature='%s'",
        req.bundle_id, req.doc_type, feature,
    )
    try:
        result = document_agent.retry_document(
            canvas=req.canvas,
            bundle_id=req.bundle_id,
            doc_type=req.doc_type,
        )
    except Exception as exc:
        logger.error("[documents/retry] error: %s", exc)
        raise HTTPException(502, f"Retry failed: {exc}")

    logger.info("[documents/retry] new job_id=%s", result.get("job_id"))
    return result


class DownloadRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    content: str
    # Job ID for native high-quality DOCX (pipeline-generated)
    docgen_job_id: Optional[str] = Field(default=None, alias="_docgen_job_id")
    # Bundle ID + doc_type enable direct session-path lookup without JOBS in memory
    bundle_id: Optional[str]     = Field(default=None, alias="_bundle_id")
    doc_type:  Optional[str]     = Field(default=None, alias="_doc_type")


@app.post("/api/documents/download")
def download_document(req: DownloadRequest):
    """
    Download a DOCX for a document.

    Priority order:
      1. Pipeline-generated DOCX — read directly from the job output directory on disk.
         Gives the highest-quality result (proper styles, tables, diagrams).
      2. Markdown-to-DOCX fallback — generates a basic .docx from the markdown content
         using python-docx (used for fallback/local-preview docs).
    """
    import io
    from fastapi.responses import StreamingResponse

    job_id    = req.docgen_job_id
    bundle_id = req.bundle_id
    doc_type  = req.doc_type

    # ── 1. Try to serve the pipeline-generated DOCX from disk ───────────────
    if job_id:
        try:
            import document_pipeline as dp
            from pathlib import Path as _Path

            docx_path_str = dp.get_job_output_path(job_id, bundle_id=bundle_id, doc_type=doc_type)
            if docx_path_str and _Path(docx_path_str).exists():
                buf = io.BytesIO(_Path(docx_path_str).read_bytes())
                safe_name = req.title.replace(" ", "_") + ".docx"
                logger.info("[download] Serving pipeline DOCX for job_id=%s path=%s", job_id, docx_path_str)
                return StreamingResponse(
                    buf,
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
                )
            logger.warning("[download] No DOCX found on disk for job_id=%s bundle=%s — falling back", job_id, bundle_id)
        except Exception as exc:
            logger.warning("[download] Pipeline DOCX read failed (%s) — falling back", exc)

    # ── 2. Generate from markdown content ───────────────────────────────────
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        create_formal_docx(req.title, req.content, tmp_path)
        logger.info("[download] Serving markdown-generated DOCX for '%s'", req.title)
        return FileResponse(
            tmp_path,
            filename=f"{req.title.replace(' ', '_')}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as exc:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(500, f"Failed to generate DOCX: {exc}")


@app.get("/api/documents/docx/{job_id}")
def download_docx_direct(
    job_id: str,
    title: str = "Document",
    bundle_id: Optional[str] = None,
    doc_type: Optional[str] = None,
):
    """
    Direct GET endpoint to download the pipeline-generated DOCX for a job.
    Simpler than the POST /download — no Pydantic alias issues.
    Tries all resolution levels: in-memory output_path → session path → job dir → session scan.
    Returns 404 if the pipeline DOCX does not exist on disk yet.
    """
    import document_pipeline as dp
    from pathlib import Path as _Path

    logger.info(
        "[docx/direct] job_id=%s bundle_id=%s doc_type=%s",
        job_id, bundle_id, doc_type,
    )
    docx_path_str = dp.get_job_output_path(job_id, bundle_id=bundle_id, doc_type=doc_type)
    if docx_path_str and _Path(docx_path_str).exists():
        safe_name = title.replace(" ", "_").replace("/", "-") + ".docx"
        logger.info("[docx/direct] serving %s for job_id=%s", docx_path_str, job_id)
        return FileResponse(
            docx_path_str,
            filename=safe_name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    logger.warning("[docx/direct] DOCX not found for job_id=%s bundle_id=%s", job_id, bundle_id)
    raise HTTPException(
        404,
        f"Pipeline-generated DOCX not found for job {job_id}. "
        "The document may still be generating or the output file was not saved.",
    )


@app.post("/api/documents/ppt/download")
def download_ppt(req: DownloadRequest):
    """Generate and download a .pptx version of a document."""
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        create_ppt(req.title, req.content, tmp_path)
        return FileResponse(
            tmp_path, 
            filename=f"{req.title.replace(' ', '_')}.pptx",
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(500, f"Failed to generate pptx: {str(e)}")


@app.post("/api/prototype/generate")
def generate_prototype(req: PrototypeRequest):
    """Generate UI prototype specification from canvas."""
    if not req.canvas:
        raise HTTPException(400, "canvas is required")

    prototype = prototype_agent.generate(req.canvas, req.feedback)
    return {"prototype": prototype}


@app.post("/api/execution/generate")
def generate_execution(req: ExecutionRequest):
    """Generate technical execution plan from canvas, with optional feedback."""
    if not req.canvas:
        raise HTTPException(400, "canvas is required")

    items = execution_agent.generate(req.canvas, req.feedback, req.messages)
    return items


@app.post("/api/verify/generate-test")
def generate_verify_test(req: VerifyTestRequest):
    """Generate a UPI XML test case from a prompt."""
    xml = test_agent.generate_xml(req.prompt, req.canvas)
    return {"xml": xml}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_thinking_steps(raw_thinking: str, feature_name: str) -> list:
    """
    Parse raw <think> content into structured steps, or generate default steps.
    """
    if raw_thinking and len(raw_thinking) > 100:
        # Try to split thinking into logical steps
        paragraphs = [p.strip() for p in raw_thinking.split("\n\n") if p.strip()]
        if len(paragraphs) >= 3:
            steps = []
            labels = [
                "Parsing feature requirements",
                "Analyzing relevant RBI Master Directions",
                "Reviewing NPCI Operational Circulars",
                "Mapping ecosystem landscape",
                "Identifying differentiation angle",
                "Drafting canvas sections 1–5",
                "Drafting canvas sections 6–10",
                "Compliance cross-check",
                "Finalizing technical roadmap",
            ]
            for i, para in enumerate(paragraphs[:9]):
                steps.append({
                    "label": labels[i] if i < len(labels) else f"Analysis step {i+1}",
                    "detail": para[:300],
                    "duration": max(600, min(1800, len(para) * 3)),
                })
            return steps

    # Default thinking steps
    return [
        {"label": "Parsing feature requirements", "detail": f'Breaking down the scope for "{feature_name}". Identifying: target users, core UPI hooks, phase context, RBI applicability.', "duration": 900},
        {"label": "Analyzing Relevant RBI Master Directions", "detail": "Master Direction on Digital Payment Security Controls (Feb 2021). Key: §4 MFA mandatory, §6 TLS 1.3+, §9 DSC validation, §12 5-year audit trails.", "duration": 1200},
        {"label": "Reviewing NPCI Operational Circulars", "detail": "Analyzing applicable UPI circulars for mandates, block/amount limits, life-cycle notifications, and T+1 grievance resolution requirements.", "duration": 1000},
        {"label": "Mapping ecosystem landscape", "detail": f"PSPs: PhonePe (48%), GPay (37%), Paytm, CRED. Issuers: SBI (520M accts), HDFC, ICICI, Axis. Merchants: Zomato, Uber, Blinkit, Zepto. Analyzing fit for {feature_name}.", "duration": 1100},
        {"label": "Identifying differentiation angle", "detail": f"EXPONENTIAL vs incremental for {feature_name}. Aligns with RBI Payments Vision 2025. Addresses 18% cart abandonment and reduction in checkout friction.", "duration": 900},
        {"label": "Drafting canvas sections 1–5", "detail": "Feature (layman + user journey), Need (why + differentiation), Market View (ecosystem response + regulatory), Scalability (demand/supply anchors), Validation (MVP + pilot + data KPIs).", "duration": 1400},
        {"label": "Drafting canvas sections 6–10", "detail": "Product Operating (3 KPIs + grievance via UDIR), Product Comms (circular + documentation), Pricing (3-yr view), Risks (fraud/infosec), Compliance (all applicable regulations).", "duration": 1300},
        {"label": "Compliance cross-check", "detail": f"Verifying all 10 canvas sections against RBI 12032, 1888, IT Act 2000, and DPDP Act 2023 for {feature_name}.", "duration": 800},
    ]


@app.post("/api/product/certify")
def certify_product(req: CertifyRequest):
    """
    Run the autonomous certification workflow.
    """
    return certification_agent.certify(
        feature_name=req.featureName,
        canvas=req.canvas,
        change_manifest=req.changeManifest,
        test_results=req.testResults
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
