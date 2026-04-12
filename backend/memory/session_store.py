"""
In-memory session store.
Designed so every field can later be persisted to PostgreSQL with minimal changes.
"""
import uuid
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field


@dataclass
class RequirementState:
    feature_request: str = ""
    messages: list[dict] = field(default_factory=list)   # [{role, content}]
    questions_asked: int = 0
    answers: dict = field(default_factory=dict)           # question_key -> answer
    structured_output: Optional[dict] = None
    status: str = "clarifying"                            # clarifying | complete


@dataclass
class ResearchState:
    status: str = "idle"                                  # idle | generating | ready
    reports: list[dict] = field(default_factory=list)    # version history
    current_version: int = 0
    feedback_history: list[str] = field(default_factory=list)


@dataclass
class CanvasState:
    status: str = "idle"                                  # idle | generating | ready
    canvases: list[dict] = field(default_factory=list)   # version history
    current_version: int = 0


@dataclass
class Session:
    session_id: str
    created_at: datetime
    requirement: RequirementState = field(default_factory=RequirementState)
    research: ResearchState = field(default_factory=ResearchState)
    canvas: CanvasState = field(default_factory=CanvasState)


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        sid = str(uuid.uuid4())
        session = Session(session_id=sid, created_at=datetime.utcnow())
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())


# Singleton — import this across the app
store = SessionStore()
