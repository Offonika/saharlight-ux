import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..schemas.user import UserContext
from ..services.onboarding_events import get_onboarding_status
from ..telegram_auth import require_tg_user

logger = logging.getLogger(__name__)

router = APIRouter()


class OnboardingStatusResponse(BaseModel):
    step: int | None = None
    missingSteps: list[int] = Field(default_factory=list)


@router.get("/onboarding/status", response_model=OnboardingStatusResponse)
async def status(
    telegram_id: int = Query(alias="telegramId"),
    user: UserContext = Depends(require_tg_user),
) -> OnboardingStatusResponse:
    if telegram_id != user["id"]:
        raise HTTPException(status_code=403, detail="telegram id mismatch")
    step, missing = await get_onboarding_status(telegram_id)
    return OnboardingStatusResponse(step=step, missingSteps=missing)
