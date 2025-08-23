from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

from sqlalchemy import create_engine

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from services.api.app.diabetes.handlers import dose_calc
from services.api.app.diabetes.utils.constants import XE_GRAMS


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
    update = DummyUpdate(
        message=DummyMessage(text), effective_user=SimpleNamespace(id=1)
    )
    context = DummyContext(user_data={}, chat_data={})
    return update, context


@pytest.mark.asyncio
async def test_cancel_then_calls_cancel_first(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def dummy_cancel(
        update: Update,
        context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
    ) -> int:
        calls.append("cancel")
        return int(ConversationHandler.END)

    async def handler(
        update: Update,
        context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
    ) -> int:
        calls.append("handler")
        return 42

    monkeypatch.setattr(dose_calc, "dose_cancel", dummy_cancel)

    wrapped = dose_calc._cancel_then(handler)
    result = await wrapped(
        cast(Update, DummyUpdate(DummyMessage(), SimpleNamespace())),
        cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            DummyContext({}, {}),
        ),
    )

    assert result == 42
    assert calls == ["cancel", "handler"]


@pytest.mark.asyncio
async def test_dose_xe_valid_input() -> None:
    update, context = make_update_context("1.5")

    result = await dose_calc.dose_xe(
        cast(Update, update),
        cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            context,
        ),
    )

    assert result == dose_calc.DOSE_SUGAR
    entry = context.user_data.get("pending_entry")
    assert entry is not None and entry["xe"] == 1.5
    assert any("сахар" in reply.lower() for reply in update.message.replies)


@pytest.mark.asyncio
async def test_dose_xe_rejects_non_numeric() -> None:
    update, context = make_update_context("abc")

    result = await dose_calc.dose_xe(
        cast(Update, update),
        cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            context,
        ),
    )

    assert result == dose_calc.DOSE_XE
    assert any("число" in reply.lower() for reply in update.message.replies)


@pytest.mark.asyncio
async def test_dose_carbs_negative() -> None:
    update, context = make_update_context("-1")

    result = await dose_calc.dose_carbs(
        cast(Update, update),
        cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            context,
        ),
    )

    assert result == dose_calc.DOSE_CARBS
    assert any(
        "не может быть отриц" in reply.lower() for reply in update.message.replies
    )


@dataclass
class DummyProfile:
    icr: float | None
    cf: float | None
    target_bg: float | None


class DummySession:
    def __init__(self, profile: DummyProfile | None) -> None:
        self._profile = profile
        self._engine = create_engine("sqlite://")

    def __enter__(self) -> DummySession:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def get(self, model: object, user_id: int) -> DummyProfile | None:
        return self._profile

    def get_bind(self, **_: Any) -> Any:
        return self._engine

    def commit(self) -> None:
        return None


@pytest.mark.asyncio
async def test_dose_sugar_profile_required(monkeypatch: pytest.MonkeyPatch) -> None:
    update, context = make_update_context("5")
    context.user_data["pending_entry"] = {"carbs_g": 10}

    monkeypatch.setattr(dose_calc, "SessionLocal", lambda: DummySession(None))
    monkeypatch.setattr(dose_calc, "menu_keyboard", "menu")

    result = await dose_calc.dose_sugar(
        cast(Update, update),
        cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            context,
        ),
    )

    assert result == dose_calc.END
    assert any("профиль не настроен" in r.lower() for r in update.message.replies)
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_dose_sugar_success(monkeypatch: pytest.MonkeyPatch) -> None:
    update, context = make_update_context("6")
    context.user_data["pending_entry"] = {"carbs_g": 12}

    profile = DummyProfile(icr=10.0, cf=2.0, target_bg=5.5)

    monkeypatch.setattr(dose_calc, "SessionLocal", lambda: DummySession(profile))
    monkeypatch.setattr(dose_calc, "calc_bolus", lambda carbs, sugar, patient: 3.0)
    monkeypatch.setattr(dose_calc, "confirm_keyboard", lambda: "confirm")

    result = await dose_calc.dose_sugar(
        cast(Update, update),
        cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            context,
        ),
    )

    assert result == dose_calc.END
    assert any("ваша доза: 3.0" in r.lower() for r in update.message.replies)
    entry = context.user_data.get("pending_entry")
    assert entry is not None and entry["dose"] == 3.0


@pytest.mark.asyncio
async def test_dose_sugar_converts_xe(monkeypatch: pytest.MonkeyPatch) -> None:
    update, context = make_update_context("6")
    context.user_data["pending_entry"] = {"xe": 2.0}

    profile = DummyProfile(icr=10.0, cf=2.0, target_bg=5.5)

    monkeypatch.setattr(dose_calc, "SessionLocal", lambda: DummySession(profile))
    monkeypatch.setattr(dose_calc, "calc_bolus", lambda carbs, sugar, patient: 3.0)
    monkeypatch.setattr(dose_calc, "confirm_keyboard", lambda: "confirm")

    result = await dose_calc.dose_sugar(
        cast(Update, update),
        cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            context,
        ),
    )

    assert result == dose_calc.END
    entry = context.user_data.get("pending_entry")
    assert entry is not None
    assert entry["carbs_g"] == XE_GRAMS * 2.0
