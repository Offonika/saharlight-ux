from __future__ import annotations

import json
import importlib
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from telegram import Update
from telegram.ext import CallbackContext

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
