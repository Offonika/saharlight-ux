import asyncio
import datetime
import os
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
from services.api.app.diabetes.handlers import dose_calc


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


class DummySession:
    def __init__(self, profile: Any) -> None:
        self.profile = profile

    def __enter__(self) -> "DummySession":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def get(self, model: object, user_id: int) -> Any:
        return self.profile


@pytest.mark.asyncio
async def test_dose_sugar_requires_carbs_or_xe() -> None:
    entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    message = DummyMessage("5.5")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": entry}),
    )

    result = await dose_calc.dose_sugar(update, context)

    assert result == dose_calc.DoseState.METHOD
    assert message.replies and "углев" in message.replies[0].lower()
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_dose_sugar_requires_pending_entry() -> None:
    message = DummyMessage("5.5")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    result = await dose_calc.dose_sugar(update, context)

    assert result == dose_calc.DoseState.METHOD
    assert message.replies and "углев" in message.replies[0].lower()
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_dose_sugar_uses_async_db(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "carbs_g": 10,
    }
    message = DummyMessage("5.5")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": entry}),
    )

    profile = SimpleNamespace(icr=10.0, cf=2.0, target_bg=5.5)
    monkeypatch.setattr(dose_calc, "SessionLocal", lambda: DummySession(profile))
    monkeypatch.setattr(dose_calc, "run_db", None)

    called = False

    async def fake_to_thread(func: Callable[[], Any], /) -> Any:
        nonlocal called
        called = True
        return func()

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(dose_calc, "calc_bolus", lambda carbs, sugar, patient: 1.0)
    monkeypatch.setattr(dose_calc, "confirm_keyboard", lambda: "confirm")

    result = await dose_calc.dose_sugar(update, context)

    assert result == dose_calc.END
    assert called


@pytest.mark.asyncio
async def test_dose_sugar_missing_carbs(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "xe": 1.0,
    }
    message = DummyMessage("5.5")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": entry}),
    )

    profile = SimpleNamespace(icr=10.0, cf=2.0, target_bg=5.5)

    async def fake_run_db(func: Callable[[Any], Any], sessionmaker: Any) -> Any:
        return profile

    monkeypatch.setattr(dose_calc, "run_db", fake_run_db)

    class MulNone:
        def __mul__(self, other: float) -> Any:
            return None

        __rmul__ = __mul__

    monkeypatch.setattr(dose_calc, "XE_GRAMS", MulNone())

    result = await dose_calc.dose_sugar(update, context)

    assert result == dose_calc.END
    assert any("расчёт невозможен" in r.lower() for r in message.replies)
    assert context.user_data == {}
