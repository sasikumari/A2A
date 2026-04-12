from fastapi import APIRouter, HTTPException
from memory.session_store import store
from schemas.models import (
    RequirementStartRequest,
    RequirementRespondRequest,
    RequirementStateResponse,
    AgentMessage,
)
from agents.requirement_agent import start_requirement_gathering, answer_clarification

router = APIRouter(prefix="/requirement", tags=["Requirement Agent"])


def _to_response(session_id: str, state: dict) -> RequirementStateResponse:
    messages = [AgentMessage(role=m["role"], content=m["content"]) for m in state.get("messages", [])]
    return RequirementStateResponse(
        session_id=session_id,
        status=state.get("status", "clarifying"),
        messages=messages,
        questions_asked=state.get("questions_asked", 0),
        structured_output=state.get("structured_output"),
    )


@router.post("/start", response_model=RequirementStateResponse)
async def start(req: RequirementStartRequest):
    if not store.exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    session = store.get(req.session_id)
    session.requirement.feature_request = req.feature_request
    session.requirement.status = "clarifying"

    state = await start_requirement_gathering(req.session_id, req.feature_request)

    # Sync to session store
    session.requirement.messages = state.get("messages", [])
    session.requirement.questions_asked = state.get("questions_asked", 0)
    session.requirement.structured_output = state.get("structured_output")
    session.requirement.status = state.get("status", "clarifying")

    return _to_response(req.session_id, state)


@router.post("/respond", response_model=RequirementStateResponse)
async def respond(req: RequirementRespondRequest):
    if not store.exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    state = await answer_clarification(req.session_id, req.answer)

    session = store.get(req.session_id)
    session.requirement.messages = state.get("messages", [])
    session.requirement.questions_asked = state.get("questions_asked", 0)
    session.requirement.structured_output = state.get("structured_output")
    session.requirement.status = state.get("status", "clarifying")

    return _to_response(req.session_id, state)


@router.get("/{session_id}", response_model=RequirementStateResponse)
async def get_state(session_id: str):
    if not store.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    session = store.get(session_id)
    req = session.requirement
    return RequirementStateResponse(
        session_id=session_id,
        status=req.status,
        messages=[AgentMessage(role=m["role"], content=m["content"]) for m in req.messages],
        questions_asked=req.questions_asked,
        structured_output=req.structured_output,
    )
