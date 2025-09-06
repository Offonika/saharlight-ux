from datetime import datetime

import pytest

from services.api.app.diabetes.services.db import SubStatus
from tests.test_billing_trial import make_client, setup_db


def test_trial_response_contains_end_date(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.post("/api/billing/trial", params={"user_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "pro"
    assert data["status"] == SubStatus.trial.value
    assert "endDate" in data and data["endDate"]
    # ensure endDate is valid ISO format
    datetime.fromisoformat(data["endDate"])
