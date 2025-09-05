from __future__ import annotations

from fastapi.testclient import TestClient

from prometheus_client import CONTENT_TYPE_LATEST

from services.api.app.diabetes.metrics import (
    lessons_completed,
    lessons_started,
    quiz_avg_score,
)


def test_prometheus_metrics_endpoint() -> None:
    """Prometheus metrics are exposed on /metrics."""

    lessons_started.inc()
    lessons_completed.inc()
    quiz_avg_score.observe(50)

    from services.api.app.main import app

    with TestClient(app) as client:
        resp = client.get("/metrics")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == CONTENT_TYPE_LATEST
    body = resp.text
    assert "lessons_started" in body
    assert "lessons_completed" in body
    assert "quiz_avg_score_sum" in body
