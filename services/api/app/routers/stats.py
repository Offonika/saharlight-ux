import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas.stats import AnalyticsPoint, DayStats
from ..schemas.user import UserContext
from ..services.stats import get_day_stats
from ..telegram_auth import require_tg_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=DayStats | dict[str, object])
async def get_stats(
    telegram_id: int = Query(alias="telegramId"),
    user: UserContext = Depends(require_tg_user),
) -> DayStats | dict[str, object]:
    if telegram_id != user["id"]:
        raise HTTPException(status_code=403, detail="telegram id mismatch")
    stats = await get_day_stats(telegram_id)
    if stats is None:
        return {}
    return stats


@router.get("/analytics")
async def get_analytics(
    telegram_id: int = Query(alias="telegramId"),
    user: UserContext = Depends(require_tg_user),
) -> list[AnalyticsPoint]:
    if telegram_id != user["id"]:
        raise HTTPException(status_code=403, detail="telegram id mismatch")
    return [
        AnalyticsPoint(date="2024-01-01", sugar=5.5),
        AnalyticsPoint(date="2024-01-02", sugar=6.1),
        AnalyticsPoint(date="2024-01-03", sugar=5.8),
        AnalyticsPoint(date="2024-01-04", sugar=6.0),
        AnalyticsPoint(date="2024-01-05", sugar=5.4),
    ]
