import asyncio
from fastapi import APIRouter, HTTPException
from memory.session_store import store
from schemas.models import (
    ResearchGenerateRequest,
    ResearchFeedbackRequest,
    ResearchStateResponse,
    ResearchReport,
    ResearchSection,
)
from agents.research_agent import generate_research, regenerate_with_feedback

router = APIRouter(prefix="/research", tags=["Research Agent"])


def _build_report(raw: dict) -> ResearchReport:
    versions = raw.get("report_versions", [])
    current_v = raw.get("current_version", 1)
    # Find the latest version dict
    report_dict = next((r for r in versions if r["version"] == current_v), versions[-1] if versions else {})
    sections = [
        ResearchSection(
            title=s.get("title", s.get("key", "")),
            content=s.get("content", ""),
            sources=s.get("sources", []),
        )
        for s in report_dict.get("sections", [])
    ]
    return ResearchReport(
        version=current_v,
        sections=sections,
        summary=report_dict.get("summary", ""),
    )


@router.post("/generate", response_model=ResearchStateResponse)
async def generate(req: ResearchGenerateRequest):
    if not store.exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    session = store.get(req.session_id)
    structured_output = session.requirement.structured_output

    if not structured_output:
        raise HTTPException(status_code=400, detail="Requirement gathering not complete yet")

    session.research.status = "generating"
    state = await asyncio.to_thread(generate_research, req.session_id, structured_output)

    session.research.status = state.get("status", "ready")
    session.research.current_version = state.get("current_version", 1)
    session.research.reports = state.get("report_versions", [])
    store.save(req.session_id)

    report = _build_report(state)
    return ResearchStateResponse(
        session_id=req.session_id,
        status=state.get("status", "ready"),
        current_report=report,
        versions=[r["version"] for r in state.get("report_versions", [])],
    )


@router.post("/feedback", response_model=ResearchStateResponse)
async def feedback(req: ResearchFeedbackRequest):
    if not store.exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    session = store.get(req.session_id)
    session.research.status = "regenerating"
    session.research.feedback_history.append(req.feedback)

    state = await asyncio.to_thread(
        regenerate_with_feedback,
        req.session_id,
        req.feedback,
        req.sections_to_regenerate,
    )

    session.research.status = state.get("status", "ready")
    session.research.current_version = state.get("current_version", 1)
    session.research.reports = state.get("report_versions", [])
    store.save(req.session_id)

    report = _build_report(state)
    return ResearchStateResponse(
        session_id=req.session_id,
        status=state.get("status", "ready"),
        current_report=report,
        versions=[r["version"] for r in state.get("report_versions", [])],
    )


@router.get("/{session_id}", response_model=ResearchStateResponse)
async def get_state(session_id: str):
    if not store.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    session = store.get(session_id)
    research = session.research

    if not research.reports:
        return ResearchStateResponse(
            session_id=session_id,
            status=research.status,
            current_report=None,
            versions=[],
        )

    # Build from stored report data
    current_v = research.current_version
    report_dict = next((r for r in research.reports if r["version"] == current_v), research.reports[-1])
    sections = [
        ResearchSection(
            title=s.get("title", ""),
            content=s.get("content", ""),
            sources=s.get("sources", []),
        )
        for s in report_dict.get("sections", [])
    ]
    report = ResearchReport(
        version=current_v,
        sections=sections,
        summary=report_dict.get("summary", ""),
    )
    return ResearchStateResponse(
        session_id=session_id,
        status=research.status,
        current_report=report,
        versions=[r["version"] for r in research.reports],
    )
