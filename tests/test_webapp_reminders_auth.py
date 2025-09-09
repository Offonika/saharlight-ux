import hashlib
import hmac
import json
import time
import urllib.parse
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.main as server
from services.api.app.config import settings
from services.api.app.diabetes.services.db import Base, User
from services.api.app.services import reminders

TOKEN = "test-token"


def build_init_data(token: str = TOKEN, user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {
        "auth_date": str(int(time.time())),
        "query_id": "abc",
        "user": user,
    }
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    monkeypatch.setattr(reminders, "SessionLocal", TestSession)
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()
    try:
        with TestClient(server.app) as test_client:
            yield test_client
    finally:
        engine.dispose()


def test_reminders_authorized_without_role(client: TestClient) -> None:
    init_data = build_init_data()
    resp = client.get(
        "/api/reminders",
        params={"telegramId": 1},
        headers={"Authorization": f"tg {init_data}"},
    )
    assert resp.status_code == 200
