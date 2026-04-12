from fastapi import APIRouter
from memory.session_store import store
from schemas.models import SessionCreateResponse

router = APIRouter(prefix="/session", tags=["Session"])


@router.post("/create", response_model=SessionCreateResponse)
async def create_session():
    session = store.create()
    return SessionCreateResponse(session_id=session.session_id)


@router.get("/list")
async def list_sessions():
    return {"sessions": store.list_sessions()}


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    store.delete(session_id)
    return {"deleted": session_id}
