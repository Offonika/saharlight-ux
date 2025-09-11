import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..schemas.stats import AnalyticsPoint, DayStats
from ..schemas.user import UserContext
from ..services.stats import get_day_stats
from ..telegram_auth import check_token

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/stats",
    response_model=DayStats,
    responses={204: {"description": "No Content - no statistics available."}},
)
async def get_stats(
    telegram_id: int = Query(alias="telegramId"),
    user: UserContext = Depends(check_token),
) -> DayStats | Response:
    if telegram_id != user["id"]:
        raise HTTPException(status_code=403, detail="telegram id mismatch")
    stats = await get_day_stats(telegram_id)
    if stats is None:
        return Response(status_code=204)
    return stats


@router.get("/analytics")
async def get_analytics(
    telegram_id: int = Query(alias="telegramId"),
    user: UserContext = Depends(check_token),
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
