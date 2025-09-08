from __future__ import annotations

from fastapi.testclient import TestClient

from prometheus_client import CONTENT_TYPE_LATEST

import pytest
from services.api.app.config import settings
from services.api.app.diabetes.metrics import (
    lessons_completed,
    lessons_started,
    quiz_avg_score,
)
from services.api.app.telegram_auth import TG_INIT_DATA_HEADER
from tests.test_telegram_auth import TOKEN, build_init_data


def test_prometheus_metrics_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prometheus metrics are exposed on /api/metrics."""

    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data()

    lessons_started.inc()
    lessons_completed.inc()
    quiz_avg_score.observe(50)

    from services.api.app.main import app

    with TestClient(app) as client:
        resp = client.get("/api/metrics", headers={TG_INIT_DATA_HEADER: init_data})

    assert resp.status_code == 200
    assert resp.headers["content-type"] == CONTENT_TYPE_LATEST
    body = resp.text
    assert "lessons_started" in body
    assert "lessons_completed" in body
    assert "quiz_avg_score_sum" in body


def test_prometheus_metrics_requires_auth() -> None:
    from services.api.app.main import app

    with TestClient(app) as client:
        resp = client.get("/api/metrics")

    assert resp.status_code == 401
