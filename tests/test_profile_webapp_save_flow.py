from __future__ import annotations

import json
import importlib
from datetime import time as dt_time
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.services.db as db
from services.api.app.diabetes.services.db import Base, User
import services.api.app.services.profile as profile_service
from services.api.app.schemas.profile import ProfileSchema

handlers = importlib.import_module(
    "services.api.app.diabetes.handlers.profile.conversation"
)


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.web_app_data: Any | None = None

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)


ERROR_MSG = "⚠️ Некорректные данные из WebApp."


@pytest.mark.asyncio
async def test_webapp_save_payload_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    post_mock = MagicMock()
    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    msg = DummyMessage()
    msg.web_app_data = SimpleNamespace(data=json.dumps({"icr": 1}))
    update = cast(
        Update,
        SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await handlers.profile_webapp_save(update, context)
    assert post_mock.call_count == 0
    assert msg.texts == [ERROR_MSG]


@pytest.mark.asyncio
async def test_webapp_save_negative_value(monkeypatch: pytest.MonkeyPatch) -> None:
    post_mock = MagicMock()
    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    msg = DummyMessage()
    msg.web_app_data = SimpleNamespace(
        data=json.dumps({"icr": -1, "cf": 3, "target": 6, "low": 4, "high": 9})
    )
    update = cast(
        Update,
        SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await handlers.profile_webapp_save(update, context)
    assert post_mock.call_count == 0
    assert msg.texts == [handlers.MSG_ICR_GT0]


@pytest.mark.asyncio
async def test_webapp_save_comma_decimal(monkeypatch: pytest.MonkeyPatch) -> None:
    post_mock = MagicMock(return_value=(True, None))
    save_mock = MagicMock(return_value=True)

    async def run_db(func, sessionmaker):
        session = MagicMock()
        return func(session)

    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    monkeypatch.setattr(handlers, "save_profile", save_mock)
    monkeypatch.setattr(handlers, "run_db", run_db)

    msg = DummyMessage()
    msg.web_app_data = SimpleNamespace(
        data=json.dumps(
            {"icr": "8,5", "cf": "3", "target": "6", "low": "4,2", "high": "9"}
        )
    )
    update = cast(
        Update,
        SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await handlers.profile_webapp_save(update, context)
    assert post_mock.call_count == 1
    assert post_mock.call_args[0][3:] == (1, 8.5, 3.0, 6.0, 4.2, 9.0)
    save_mock.assert_called_once()
    text = msg.texts[0]
    assert "ИКХ: 8.5" in text
    assert "Низкий порог: 4.2" in text


def test_parse_profile_values_comma() -> None:
    result = handlers.parse_profile_values(
        {"icr": "8,5", "cf": "3", "target": "6", "low": "4,2", "high": "9"}
    )
    assert result == (8.5, 3.0, 6.0, 4.2, 9.0)


def test_parse_profile_values_invalid_number() -> None:
    with pytest.raises(ValueError):
        handlers.parse_profile_values(
            {"icr": "x", "cf": "3", "target": "6", "low": "4", "high": "9"}
        )


@pytest.mark.asyncio
async def test_save_profile_partial_icr_cf(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    initial = ProfileSchema(
        telegramId=1,
        icr=1.0,
        cf=1.0,
        target=5.0,
        low=4.0,
        high=6.0,
        quietStart=dt_time(1, 0),
        quietEnd=dt_time(2, 0),
        timezone="Europe/Moscow",
        timezoneAuto=False,
        sosAlertsEnabled=False,
    )
    await profile_service.save_profile(initial)

    update = ProfileSchema(
        telegramId=1,
        icr=2.0,
        cf=2.0,
        target=5.0,
        low=4.0,
        high=6.0,
    )
    await profile_service.save_profile(update)

    prof = await profile_service.get_profile(1)
    assert prof.icr == 2.0
    assert prof.cf == 2.0
    assert prof.quiet_start == dt_time(1, 0)
    assert prof.quiet_end == dt_time(2, 0)
    assert prof.timezone == "Europe/Moscow"
    assert prof.timezone_auto is False
    assert prof.sos_alerts_enabled is False
    engine.dispose()


@pytest.mark.asyncio
async def test_profile_view_uses_local_profile_on_stale_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(profile_service.db, "SessionLocal", TestSession)

    async def run_db(func, sessionmaker):
        with sessionmaker() as session:
            return func(session)

    monkeypatch.setattr(handlers, "run_db", run_db)
    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    post_mock = MagicMock(return_value=(True, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)

    msg = DummyMessage()
    payload = {"icr": 8, "cf": 3, "target": 6, "low": 4, "high": 9}
    msg.web_app_data = SimpleNamespace(data=json.dumps(payload))
    update = cast(
        Update,
        SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await handlers.profile_webapp_save(update, context)

    outdated = SimpleNamespace(icr=1, cf=2, target=None, low=None, high=None)
    monkeypatch.setattr(handlers, "fetch_profile", lambda api, exc, uid: outdated)

    msg_view = DummyMessage()
    update_view = cast(
        Update, SimpleNamespace(message=msg_view, effective_user=SimpleNamespace(id=1))
    )
    await handlers.profile_view(update_view, context)

    text = msg_view.texts[0]
    assert "ИКХ: 8" in text
    assert "КЧ: 3" in text
    assert "Целевой сахар: 6" in text
    engine.dispose()


@pytest.mark.asyncio
async def test_webapp_save_persists_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(profile_service.db, "SessionLocal", TestSession)

    async def run_db(func, *args, sessionmaker, **kwargs):
        with sessionmaker() as session:
            return func(session, *args, **kwargs)

    monkeypatch.setattr(handlers, "run_db", run_db)
    monkeypatch.setattr(profile_service.db, "run_db", run_db)

    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", lambda *a, **kw: (True, None))

    msg = DummyMessage()
    payload = {
        "icr": 8,
        "cf": 3,
        "target": 6,
        "low": 4,
        "high": 9,
        "timezone": "Europe/Moscow",
        "timezoneAuto": False,
        "dia": 12,
        "carbUnits": "xe",
        "glucoseUnits": "mg/dL",
        "deviceTz": "Europe/Moscow",
    }
    msg.web_app_data = SimpleNamespace(data=json.dumps(payload))
    update = cast(
        Update,
        SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await handlers.profile_webapp_save(update, context)

    settings = await profile_service.get_profile_settings(1)
    assert settings.timezone == "Europe/Moscow"
    assert settings.dia == 12
    assert settings.carbUnits.value == "xe"
    assert settings.glucoseUnits.value == "mg/dL"
    engine.dispose()
