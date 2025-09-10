from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from unittest.mock import AsyncMock

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
import services.api.app.diabetes.services.users as users_service
import services.api.app.diabetes.services.db as db
import services.api.app.services.onboarding_state as onboarding_state


@pytest.fixture(autouse=True)
def fake_state(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[int, dict[str, Any]] = {}
    steps: dict[int, int] = {}
    variants: dict[int, str | None] = {}

    engine = create_engine("sqlite:///:memory:")
    db.Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    async def run_db(
        fn: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:  # pragma: no cover - simple sync stub
        session_maker = kwargs.pop("sessionmaker", TestSession)
        with session_maker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(onboarding, "SessionLocal", TestSession, raising=False)
    monkeypatch.setattr(users_service, "SessionLocal", TestSession, raising=False)
    monkeypatch.setattr(onboarding, "run_db", run_db, raising=False)
    monkeypatch.setattr(users_service, "run_db", run_db, raising=False)

    async def save_state(
        user_id: int, step: int, data: dict[str, object], variant: str | None = None
    ) -> None:
        steps[user_id] = step
        save_data = dict(data)
        if isinstance(save_data.get("reminders"), set):
            save_data["reminders"] = list(save_data["reminders"])
        store[user_id] = save_data
        variants[user_id] = variant

    class DummyState:
        def __init__(self, uid: int) -> None:
            self.user_id = uid
            self.step = steps[uid]
            self.data = store[uid]
            self.variant = variants[uid]
            self.completed_at = None

    async def load_state(user_id: int) -> DummyState | None:
        if user_id not in steps:
            return None
        return DummyState(user_id)

    async def complete_state(user_id: int) -> None:  # pragma: no cover - no logic
        pass

    monkeypatch.setattr(onboarding_state, "save_state", save_state)
    monkeypatch.setattr(onboarding_state, "load_state", load_state)
    monkeypatch.setattr(onboarding_state, "complete_state", complete_state)

    async def noop_mark(user_id: int) -> None:  # pragma: no cover - no logic
        pass

    monkeypatch.setattr(onboarding, "_mark_user_complete", noop_mark)

    async def fake_save_timezone(uid: int, tz: str, *, auto: bool) -> bool:
        return True

    monkeypatch.setattr(onboarding, "save_timezone", fake_save_timezone)

    async def fake_create_reminder_from_preset(
        user_id: int, code: str, job_queue: Any
    ) -> Any:
        return SimpleNamespace(type=code, is_enabled=True)

    def fake_describe(rem: Any, user: Any | None = None) -> str:
        return f"R {getattr(rem, 'type', '')}"

    monkeypatch.setattr(
        onboarding.reminder_handlers,
        "create_reminder_from_preset",
        fake_create_reminder_from_preset,
    )
    monkeypatch.setattr(
        onboarding.reminder_handlers,
        "_describe",
        fake_describe,
        raising=False,
    )


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:  # noqa: ANN401
        self.replies.append(text)

    async def reply_video(self, video: Any, **_: Any) -> None:  # noqa: ANN401
        self.replies.append(video)

    def get_bot(self) -> Any:
        return SimpleNamespace(set_my_commands=AsyncMock())


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data

    async def answer(self) -> None:  # pragma: no cover - no logic
        pass


@pytest.mark.asyncio
async def test_skip_flow_finishes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(onboarding, "choose_variant", lambda uid: "A")
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"tg_init_data": "t"}, job_queue=None),
    )

    state = await onboarding.start_command(update, context)
    assert state == onboarding.PROFILE
    assert message.replies[-1].startswith("Шаг 1/3")

    query_skip = DummyQuery(message, onboarding.CB_SKIP)
    update_skip = cast(Update, SimpleNamespace(callback_query=query_skip, effective_user=user))
    state = await onboarding.profile_chosen(update_skip, context)
    assert state == onboarding.TIMEZONE
    assert message.replies[-1].startswith("Шаг 2/3")

    message.text = "Europe/Moscow"
    update_tz = cast(Update, SimpleNamespace(message=message, effective_user=user))
    state = await onboarding.timezone_text(update_tz, context)
    assert state == onboarding.REMINDERS
    assert message.replies[-1].startswith("Шаг 3/3")

    query_rem = DummyQuery(message, f"{onboarding.CB_REMINDER_PREFIX}sugar_08")
    update_rem = cast(Update, SimpleNamespace(callback_query=query_rem, effective_user=user))
    state = await onboarding.reminders_chosen(update_rem, context)
    assert state == onboarding.REMINDERS

    query_done = DummyQuery(message, onboarding.CB_DONE)
    update_done = cast(Update, SimpleNamespace(callback_query=query_done, effective_user=user))
    state = await onboarding.reminders_chosen(update_done, context)
    assert state == ConversationHandler.END
    assert any("Готово" in r for r in message.replies)


@pytest.mark.asyncio
async def test_back_and_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(onboarding, "choose_variant", lambda uid: "A")
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"tg_init_data": "t"}, job_queue=None),
    )

    await onboarding.start_command(update, context)

    query_skip = DummyQuery(message, onboarding.CB_SKIP)
    update_skip = cast(Update, SimpleNamespace(callback_query=query_skip, effective_user=user))
    await onboarding.profile_chosen(update_skip, context)

    query_back = DummyQuery(message, onboarding.CB_BACK)
    update_back = cast(Update, SimpleNamespace(callback_query=query_back, effective_user=user))
    state = await onboarding.timezone_nav(update_back, context)
    assert state == onboarding.PROFILE

    query_cancel = DummyQuery(message, onboarding.CB_CANCEL)
    update_cancel = cast(Update, SimpleNamespace(callback_query=query_cancel, effective_user=user))
    state = await onboarding.profile_chosen(update_cancel, context)
    assert state == ConversationHandler.END


@pytest.mark.asyncio
async def test_variant_b_starts_from_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(onboarding, "choose_variant", lambda uid: "B")
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"tg_init_data": "t"}, job_queue=None),
    )

    state = await onboarding.start_command(update, context)
    assert state == onboarding.TIMEZONE
    assert message.replies[-1].startswith("Шаг 1/3")

    message.text = "Europe/Moscow"
    update_tz = cast(Update, SimpleNamespace(message=message, effective_user=user))
    state = await onboarding.timezone_text(update_tz, context)
    assert state == onboarding.PROFILE
    assert message.replies[-1].startswith("Шаг 2/3")


@pytest.mark.asyncio
async def test_start_requires_init_data() -> None:
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, job_queue=None),
    )

    state = await onboarding.start_command(update, context)
    assert state == ConversationHandler.END
    assert message.replies == ["⚠️ Откройте приложение через /start и вернитесь"]

