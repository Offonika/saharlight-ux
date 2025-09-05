import logging
from datetime import date
from typing import cast

from fastapi import APIRouter, Query, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..diabetes.services.db import SessionLocal, run_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metrics")
def get_metrics() -> Response:
    """Return Prometheus metrics."""

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/metrics/onboarding")
async def get_onboarding_metrics(
    from_: date = Query(alias="from"),
    to: date = Query(alias="to"),
    variant: str | None = None,
) -> dict[str, dict[str, dict[str, float]]]:
    """Return onboarding conversion metrics by day and variant."""

    def _query(session: Session) -> dict[str, dict[str, dict[str, float]]]:
        query = """
            SELECT date, variant, step, count
            FROM onboarding_metrics_daily
            WHERE date >= :from AND date <= :to
            """
        params: dict[str, object] = {"from": from_, "to": to}
        if variant is not None:
            query += " AND variant = :variant"
            params["variant"] = variant
        rows = session.execute(text(query), params).all()
        raw: dict[str, dict[str, dict[str, int]]] = {}
        for row in rows:
            day = str(row[0])
            var = cast(str, row[1])
            step = cast(str, row[2])
            cnt = cast(int, row[3])
            day_map = raw.setdefault(day, {})
            counts = day_map.setdefault(
                var,
                {"start": 0, "step1": 0, "step2": 0, "step3": 0, "finish": 0},
            )
            if step in counts:
                counts[step] = cnt
        result: dict[str, dict[str, dict[str, float]]] = {}
        for day, variants in raw.items():
            day_res: dict[str, dict[str, float]] = {}
            for var, counts in variants.items():
                start = counts["start"]
                if start == 0:
                    conv = {k: 0.0 for k in ("step1", "step2", "step3", "completed")}
                else:
                    conv = {
                        "step1": counts["step1"] / start,
                        "step2": counts["step2"] / start,
                        "step3": counts["step3"] / start,
                        "completed": counts["finish"] / start,
                    }
                day_res[var] = conv
            result[day] = day_res
        return result

    return await run_db(_query, sessionmaker=SessionLocal)
