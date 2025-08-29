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
async def test_webapp_save_no_data(monkeypatch: pytest.MonkeyPatch) -> None:
    post_mock = MagicMock()
    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    msg = DummyMessage()
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
async def test_webapp_save_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post_mock = MagicMock()
    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    msg = DummyMessage()
    msg.web_app_data = SimpleNamespace(data="{bad")
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
async def test_webapp_save_missing_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    post_mock = MagicMock()
    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    msg = DummyMessage()
    msg.web_app_data = SimpleNamespace(
        data=json.dumps({"icr": 1, "cf": 2, "target": 3})
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
    assert msg.texts == [ERROR_MSG]


@pytest.mark.asyncio
async def test_webapp_save_non_numeric(monkeypatch: pytest.MonkeyPatch) -> None:
    post_mock = MagicMock()
    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    msg = DummyMessage()
    msg.web_app_data = SimpleNamespace(
        data=json.dumps({"icr": "a", "cf": "b", "target": "c", "low": "d", "high": "e"})
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
    assert msg.texts == [ERROR_MSG]


@pytest.mark.parametrize(
    "payload, expected_msg",
    [
        ({"icr": 0, "cf": 3, "target": 6, "low": 4, "high": 9}, handlers.MSG_ICR_GT0),
        (
            {"icr": 8, "cf": 3, "target": 6, "low": 4, "high": 3},
            handlers.MSG_HIGH_GT_LOW,
        ),
        (
            {"icr": 8, "cf": 3, "target": 10, "low": 4, "high": 9},
            handlers.MSG_TARGET_RANGE,
        ),
    ],
)
@pytest.mark.asyncio
async def test_webapp_save_invalid_values(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, float], expected_msg: str
) -> None:
    post_mock = MagicMock()
    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    msg = DummyMessage()
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
    assert post_mock.call_count == 0
    assert msg.texts == [expected_msg]


@pytest.mark.asyncio
async def test_webapp_save_success(monkeypatch: pytest.MonkeyPatch) -> None:
    post_mock = MagicMock(return_value=(True, None))
    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    msg = DummyMessage()
    msg.web_app_data = SimpleNamespace(
        data=json.dumps({"icr": 8, "cf": 3, "target": 6, "low": 4, "high": 9})
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
    assert post_mock.call_args[0][3:] == (1, 8.0, 3.0, 6.0, 4.0, 9.0)
    text = msg.texts[0]
    assert text.startswith("✅ Профиль обновлён:")
    assert "ИКХ: 8.0" in text
    assert "КЧ: 3.0" in text
    assert "Целевой сахар: 6.0" in text
    assert "Низкий порог: 4.0" in text
    assert "Высокий порог: 9.0" in text
