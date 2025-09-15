import json
import importlib
from types import SimpleNamespace
from typing import Any, Callable, cast
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
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
    save_mock = MagicMock(return_value=True)

    async def run_db(
        func: Callable[..., object],
        sessionmaker: object,
    ) -> object:
        session = MagicMock()
        return func(session)

    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    monkeypatch.setattr(handlers, "save_profile", save_mock)
    monkeypatch.setattr(handlers, "run_db", run_db)
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
    save_mock.assert_called_once()
    assert save_mock.call_args[0][1:] == (1, 8.0, 3.0, 6.0, 4.0, 9.0)
    text = msg.texts[0]
    assert text.startswith("✅ Профиль обновлён:")
    assert "ИКХ: 8.0" in text
    assert "КЧ: 3.0" in text
    assert "Целевой сахар: 6.0" in text
    assert "Низкий порог: 4.0" in text
    assert "Высокий порог: 9.0" in text


@pytest.mark.asyncio
async def test_webapp_save_db_error(monkeypatch: pytest.MonkeyPatch) -> None:
    post_mock = MagicMock(return_value=(True, None))

    async def run_db(
        func: Callable[..., object],
        sessionmaker: object,
    ) -> object:
        session = MagicMock()
        return func(session)

    save_mock = MagicMock(return_value=False)

    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    monkeypatch.setattr(handlers, "save_profile", save_mock)
    monkeypatch.setattr(handlers, "run_db", run_db)
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
    save_mock.assert_called_once()
    assert msg.texts == ["⚠️ Не удалось сохранить профиль."]


@pytest.mark.asyncio
async def test_webapp_save_invalid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    post_mock = MagicMock()
    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    msg = DummyMessage()
    msg.web_app_data = SimpleNamespace(
        data=json.dumps(
            {"icr": 8, "cf": 3, "target": 6, "low": 4, "high": 9, "dia": 0}
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
    assert post_mock.call_count == 0
    assert msg.texts == ["Некорректные данные настроек профиля"]


@pytest.mark.asyncio
async def test_webapp_save_settings_patch_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post_mock = MagicMock(return_value=(True, None))
    save_mock = MagicMock(return_value=True)

    async def run_db(
        func: Callable[..., object],
        sessionmaker: object,
    ) -> object:
        session = MagicMock()
        return func(session)

    patch_mock = MagicMock(
        side_effect=HTTPException(status_code=500, detail="boom")
    )

    monkeypatch.setattr(handlers, "get_api", lambda: (None, None, None))
    monkeypatch.setattr(handlers, "post_profile", post_mock)
    monkeypatch.setattr(handlers, "save_profile", save_mock)
    monkeypatch.setattr(handlers, "run_db", run_db)
    monkeypatch.setattr(
        handlers.profile_service,
        "patch_user_settings",
        patch_mock,
    )
    msg = DummyMessage()
    msg.web_app_data = SimpleNamespace(
        data=json.dumps(
            {"icr": 8, "cf": 3, "target": 6, "low": 4, "high": 9, "dia": 1}
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
    patch_mock.assert_called_once()
    assert msg.texts == ["⚠️ Не удалось сохранить настройки"]


def test_parse_profile_values_success() -> None:
    result = handlers.parse_profile_values(
        {"icr": "8", "cf": "3", "target": "6", "low": "4", "high": "9"}
    )
    assert result == (8.0, 3.0, 6.0, 4.0, 9.0)


def test_parse_profile_values_error() -> None:
    with pytest.raises(ValueError) as exc:
        handlers.parse_profile_values(
            {"icr": "0", "cf": "3", "target": "6", "low": "4", "high": "9"}
        )
    assert str(exc.value) == handlers.MSG_ICR_GT0
