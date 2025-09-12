from __future__ import annotations

from sqlalchemy.orm import Session

from services.api.app.assistant.models import AssistantNote
from services.api.app.diabetes.services.repository import commit

__all__ = ["create_note"]


def create_note(session: Session, *, user_id: int, text: str) -> AssistantNote:
    """Persist a new assistant note."""
    note = AssistantNote(user_id=user_id, text=text)
    session.add(note)
    commit(session)
    session.refresh(note)
    return note
