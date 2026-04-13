from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from memory.session_store import store

router = APIRouter(prefix="/history", tags=["History"])


class RenameRequest(BaseModel):
    title: str


@router.get("")
async def list_history():
    """List all sessions ordered by most recently updated."""
    summaries = [store.get_summary(sid) for sid in store.list_sessions()]
    summaries = [s for s in summaries if s]  # filter any empty
    summaries.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return {"sessions": summaries}


@router.get("/{session_id}")
async def get_session_detail(session_id: str):
    """Return full session detail for the history portal."""
    if not store.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return store.get_detail(session_id)


@router.patch("/{session_id}/title")
async def rename_session(session_id: str, req: RenameRequest):
    """Rename a session title."""
    if not store.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    title = req.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    store.rename(session_id, title)
    return {"session_id": session_id, "title": title}


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Permanently delete a session from history."""
    if not store.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    store.delete(session_id)
    return {"deleted": session_id}
