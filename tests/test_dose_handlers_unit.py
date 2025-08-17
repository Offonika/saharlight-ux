from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from services.api.app.diabetes.handlers import dose_handlers


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, reply_markup: Any | None = None) -> None:
        self.replies.append(text)


@dataclass
class DummyUpdate:
    message: DummyMessage
    effective_user: SimpleNamespace


@dataclass
class DummyContext:
    user_data: dict[str, Any]
    chat_data: dict[str, Any]


def make_update_context(text: str) -> tuple[DummyUpdate, DummyContext]:
    update = DummyUpdate(message=DummyMessage(text), effective_user=SimpleNamespace(id=1))
    context = DummyContext(user_data={}, chat_data={})
    return update, context


def test_sanitize_removes_control_chars_and_truncates() -> None:
    text = "abc" + chr(0) + "def\n" + "x" * 50
    assert dose_handlers._sanitize(text, max_len=10) == "abcdefxxxx"


@pytest.mark.asyncio
async def test_cancel_then_calls_cancel_first(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def dummy_cancel(update: Update, context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]]) -> int:
        calls.append("cancel")
        return ConversationHandler.END

    async def handler(update: Update, context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]]) -> int:
        calls.append("handler")
        return 42

    monkeypatch.setattr(dose_handlers, "dose_cancel", dummy_cancel)

    wrapped = dose_handlers._cancel_then(handler)
    result = await wrapped(cast(Update, DummyUpdate(DummyMessage(), SimpleNamespace())), cast(CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]], DummyContext({}, {})))

    assert result == 42
    assert calls == ["cancel", "handler"]


@pytest.mark.asyncio
async def test_dose_xe_valid_input() -> None:
    update, context = make_update_context("1.5")

    result = await dose_handlers.dose_xe(cast(Update, update), cast(CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]], context))

    assert result == dose_handlers.DOSE_SUGAR
    entry = context.user_data.get("pending_entry")
    assert entry is not None and entry["xe"] == 1.5
    assert any("сахар" in reply.lower() for reply in update.message.replies)


@pytest.mark.asyncio
async def test_dose_xe_rejects_non_numeric() -> None:
    update, context = make_update_context("abc")

    result = await dose_handlers.dose_xe(cast(Update, update), cast(CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]], context))

    assert result == dose_handlers.DOSE_XE
    assert any("число" in reply.lower() for reply in update.message.replies)


@pytest.mark.asyncio
async def test_dose_carbs_negative() -> None:
    update, context = make_update_context("-1")

    result = await dose_handlers.dose_carbs(cast(Update, update), cast(CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]], context))

    assert result == dose_handlers.DOSE_CARBS
    assert any("не может быть отриц" in reply.lower() for reply in update.message.replies)


@dataclass
class DummyProfile:
    icr: float | None
    cf: float | None
    target_bg: float | None


class DummySession:
    def __init__(self, profile: DummyProfile | None) -> None:
        self._profile = profile

    def __enter__(self) -> DummySession:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def get(self, model: object, user_id: int) -> DummyProfile | None:
        return self._profile


@pytest.mark.asyncio
async def test_dose_sugar_profile_required(monkeypatch: pytest.MonkeyPatch) -> None:
    update, context = make_update_context("5")
    context.user_data["pending_entry"] = {"carbs_g": 10}

    monkeypatch.setattr(dose_handlers, "SessionLocal", lambda: DummySession(None))
    monkeypatch.setattr(dose_handlers, "menu_keyboard", "menu")

    result = await dose_handlers.dose_sugar(cast(Update, update), cast(CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]], context))

    assert result == dose_handlers.END
    assert any("профиль не настроен" in r.lower() for r in update.message.replies)
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_dose_sugar_success(monkeypatch: pytest.MonkeyPatch) -> None:
    update, context = make_update_context("6")
    context.user_data["pending_entry"] = {"carbs_g": 12}

    profile = DummyProfile(icr=10.0, cf=2.0, target_bg=5.5)

    monkeypatch.setattr(dose_handlers, "SessionLocal", lambda: DummySession(profile))
    monkeypatch.setattr(dose_handlers, "calc_bolus", lambda carbs, sugar, patient: 3.0)
    monkeypatch.setattr(dose_handlers, "confirm_keyboard", lambda: "confirm")

    result = await dose_handlers.dose_sugar(cast(Update, update), cast(CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]], context))

    assert result == dose_handlers.END
    assert any("ваша доза: 3.0" in r.lower() for r in update.message.replies)
    entry = context.user_data.get("pending_entry")
    assert entry is not None and entry["dose"] == 3.0
