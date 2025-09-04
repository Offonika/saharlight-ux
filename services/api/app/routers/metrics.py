import logging
from datetime import datetime
from typing import cast

from fastapi import APIRouter, Query, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..diabetes.services.db import SessionLocal, run_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

STEP_MAP = {
    "start": "onboarding_started",
    "step1": "step_completed_1",
    "step2": "step_completed_2",
    "step3": "step_completed_3",
    "finish": "onboarding_finished",
    "cancel": "onboarding_cancelled",
}


@router.get("/metrics/onboarding")
async def get_onboarding_metrics(
    from_: datetime = Query(alias="from"),
    to: datetime = Query(alias="to"),
) -> dict[str, dict[str, int]]:
    def _query(session: Session) -> dict[str, dict[str, int]]:
        rows = session.execute(
            text(
                """
                SELECT variant, step, count(*) AS cnt
                FROM onboarding_events
                WHERE created_at >= :from AND created_at <= :to
                GROUP BY variant, step
                """
            ),
            {"from": from_, "to": to},
        ).all()
        result: dict[str, dict[str, int]] = {}
        for row in rows:
            variant = cast(str, row[0])
            step = cast(str, row[1])
            cnt = cast(int, row[2])
            key = STEP_MAP.get(step)
            if key is None:
                continue
            counts = result.setdefault(variant, {k: 0 for k in STEP_MAP.values()})
            counts[key] = cnt
        return result

    return await run_db(_query, sessionmaker=SessionLocal)
