import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..diabetes.services.db import SessionLocal, run_db
from ..services.onboarding_events import log_onboarding_event
from ..services import onboarding_state
from ..schemas.user import UserContext
from ..telegram_auth import require_tg_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding")


class EventIn(BaseModel):
    name: str
    step: int
    variant: str | None = None


@router.post("/events")
async def post_event(data: EventIn, user: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    def _log(session: Session) -> None:
        log_onboarding_event(session, user["id"], data.name, data.step, data.variant)

    await run_db(_log, sessionmaker=SessionLocal)
    return {"status": "ok"}


class StatusOut(BaseModel):
    completed: bool
    step: int
    variant: str | None = None


@router.get("/status")
async def get_status(user: UserContext = Depends(require_tg_user)) -> StatusOut:
    state = await onboarding_state.load_state(user["id"])
    if state is None:
        return StatusOut(completed=False, step=0, variant=None)
    return StatusOut(
        completed=state.completed_at is not None,
        step=state.step,
        variant=state.variant,
    )
