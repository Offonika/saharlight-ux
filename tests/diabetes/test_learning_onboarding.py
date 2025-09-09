from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import logging

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from telegram import InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes import learning_onboarding as onboarding_utils
from services.api.app.diabetes.handlers import learning_handlers, learning_onboarding
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.services import db
from services.api.app.assistant.repositories import plans
from services.api.app.ui.keyboard import LEARN_BUTTON_TEXT


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.replies: list[str] = []
        self.markups: list[Any] = []
        self.from_user = SimpleNamespace(id=0)

    async def reply_text(
        self, text: str, **kwargs: Any
    ) -> None:  # pragma: no cover - helper
        self.replies.append(text)
        self.markups.append(kwargs.get("reply_markup"))


class DummyCallbackQuery:
    def __init__(self, data: str, message: DummyMessage) -> None:
        self.data = data
        self.message = message
        self.answers: list[str | None] = []

    async def answer(
        self, text: str | None = None, **kwargs: Any
    ) -> None:  # pragma: no cover - helper
        self.answers.append(text)


def setup_db() -> tuple[sessionmaker[Session], Engine]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    return SessionLocal, engine


@pytest.mark.asyncio
async def test_learning_onboarding_flow(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_command_model", "test-model")
    monkeypatch.setattr(settings, "learning_content_mode", "static")

    async def fake_get_profile(_: int, __: object) -> dict[str, object]:
        return {}

    monkeypatch.setattr(
        onboarding_utils.profiles, "get_profile_for_user", fake_get_profile
    )

    sample = [{"title": "Sample", "steps": ["s1"], "quiz": []}]
    path = tmp_path / "lessons.json"
    path.write_text(json.dumps(sample), encoding="utf-8")

    SessionLocal, engine = setup_db()
    await load_lessons(path, sessionmaker=SessionLocal)
    monkeypatch.setattr(learning_handlers, "SessionLocal", SessionLocal)

    try:
        message1 = DummyMessage()
        update1 = cast(Update, SimpleNamespace(message=message1, effective_user=None))
        context = cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            SimpleNamespace(user_data={}),
        )

        await learning_handlers.learn_command(update1, context)
        assert message1.replies == [onboarding_utils.AGE_PROMPT]
        markup = message1.markups[0]
        assert isinstance(markup, InlineKeyboardMarkup)
        assert [b.text for b in markup.inline_keyboard[0]] == [
            "Подросток",
            "Взрослый",
            "60+",
        ]

        message2 = DummyMessage("взрослый")
        update2 = cast(Update, SimpleNamespace(message=message2, effective_user=None))
        await learning_onboarding.onboarding_reply(update2, context)
        assert message2.replies == [onboarding_utils.LEARNING_LEVEL_PROMPT]

        message3 = DummyMessage("новичок")
        update3 = cast(Update, SimpleNamespace(message=message3, effective_user=None))
        await learning_onboarding.onboarding_reply(update3, context)
        assert any(
            LEARN_BUTTON_TEXT in text or "Урок" in text for text in message3.replies
        )
        assert context.user_data["learn_profile_overrides"] == {
            "age_group": "adult",
            "learning_level": "novice",
        }

        message5 = DummyMessage()
        update5 = cast(Update, SimpleNamespace(message=message5, effective_user=None))
        await learning_handlers.learn_command(update5, context)
        assert any(
            LEARN_BUTTON_TEXT in text or "Урок" in text for text in message5.replies
        )

        message_reset = DummyMessage()
        update_reset = cast(
            Update, SimpleNamespace(message=message_reset, effective_user=None)
        )
        context.user_data["learn_profile_overrides"] = {"a": 1}
        context.user_data["learn_onboarding_stage"] = "stage"
        await learning_onboarding.learn_reset(update_reset, context)
        assert "learn_profile_overrides" not in context.user_data
        assert "learn_onboarding_stage" not in context.user_data

        message6 = DummyMessage()
        update6 = cast(Update, SimpleNamespace(message=message6, effective_user=None))
        await learning_handlers.learn_command(update6, context)
        assert message6.replies == [onboarding_utils.AGE_PROMPT]
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_learning_onboarding_callback_flow(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_command_model", "test-model")
    monkeypatch.setattr(settings, "learning_content_mode", "static")

    async def fake_get_profile(_: int, __: object) -> dict[str, object]:
        return {}

    monkeypatch.setattr(
        onboarding_utils.profiles, "get_profile_for_user", fake_get_profile
    )

    sample = [{"title": "Sample", "steps": ["s1"], "quiz": []}]
    path = tmp_path / "lessons.json"
    path.write_text(json.dumps(sample), encoding="utf-8")

    SessionLocal, engine = setup_db()
    await load_lessons(path, sessionmaker=SessionLocal)
    monkeypatch.setattr(learning_handlers, "SessionLocal", SessionLocal)

    try:
        msg1 = DummyMessage()
        upd1 = cast(Update, SimpleNamespace(message=msg1, effective_user=None))
        ctx = cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            SimpleNamespace(user_data={}),
        )

        await learning_handlers.learn_command(upd1, ctx)
        assert msg1.replies == [onboarding_utils.AGE_PROMPT]

        q1_msg = DummyMessage()
        q1 = DummyCallbackQuery(f"{onboarding_utils.CB_PREFIX}adult", q1_msg)
        upd_cb1 = cast(
            Update,
            SimpleNamespace(callback_query=q1, message=None, effective_user=None),
        )
        await learning_onboarding.onboarding_callback(upd_cb1, ctx)
        assert q1_msg.replies == [onboarding_utils.LEARNING_LEVEL_PROMPT]
        markup = q1_msg.markups[0]
        assert isinstance(markup, InlineKeyboardMarkup)
        assert [b.text for b in markup.inline_keyboard[0]] == [
            "Новичок",
            "Средний",
            "Продвинутый",
        ]

        q2_msg = DummyMessage()
        q2 = DummyCallbackQuery(f"{onboarding_utils.CB_PREFIX}novice", q2_msg)
        upd_cb2 = cast(
            Update,
            SimpleNamespace(callback_query=q2, message=None, effective_user=None),
        )
        await learning_onboarding.onboarding_callback(upd_cb2, ctx)
        assert any(
            LEARN_BUTTON_TEXT in text or "Урок" in text for text in q2_msg.replies
        )
        assert ctx.user_data["learn_profile_overrides"] == {
            "age_group": "adult",
            "learning_level": "novice",
        }

        msg2 = DummyMessage()
        upd2 = cast(Update, SimpleNamespace(message=msg2, effective_user=None))
        await learning_handlers.learn_command(upd2, ctx)
        assert any(LEARN_BUTTON_TEXT in text or "Урок" in text for text in msg2.replies)
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_onboarding_reply_ignored_without_stage() -> None:
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    message = DummyMessage("hi")
    update = cast(Update, SimpleNamespace(message=message, effective_user=None))
    await learning_onboarding.onboarding_reply(update, context)
    assert message.replies == []
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_ensure_overrides_normalizes_level() -> None:
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data={
                "learn_profile_overrides": {
                    "age_group": "adult",
                    "learning_level": "продвинутый",
                }
            }
        ),
    )
    update = cast(
        Update, SimpleNamespace(message=None, callback_query=None, effective_user=None)
    )
    assert await onboarding_utils.ensure_overrides(update, context)
    assert context.user_data["learn_profile_overrides"]["learning_level"] == "expert"
    assert context.user_data.get("learning_onboarded") is True


@pytest.mark.asyncio
async def test_ensure_overrides_logs_age(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def fake_get_profile(_: int, __: object) -> dict[str, object]:
        return {}

    monkeypatch.setattr(
        onboarding_utils.profiles, "get_profile_for_user", fake_get_profile
    )
    user = SimpleNamespace(id=1)
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    msg = DummyMessage()
    upd = cast(
        Update, SimpleNamespace(message=msg, callback_query=None, effective_user=user)
    )
    with caplog.at_level(logging.INFO):
        assert not await onboarding_utils.ensure_overrides(upd, context)
    assert any(
        r.message == "ensure_overrides" and r.asked == "age" for r in caplog.records
    )
    assert any(
        r.message == "onboarding_question" and r.reason == "needs_age"
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_ensure_overrides_logs_level(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def fake_get_profile(_: int, __: object) -> dict[str, object]:
        return {"age_group": "adult"}

    monkeypatch.setattr(
        onboarding_utils.profiles, "get_profile_for_user", fake_get_profile
    )
    user = SimpleNamespace(id=1)
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    msg = DummyMessage()
    upd = cast(
        Update, SimpleNamespace(message=msg, callback_query=None, effective_user=user)
    )
    with caplog.at_level(logging.INFO):
        assert not await onboarding_utils.ensure_overrides(upd, context)
    assert any(
        r.message == "ensure_overrides" and r.asked == "level" for r in caplog.records
    )
    assert any(
        r.message == "onboarding_question" and r.reason == "needs_level"
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_lesson_command_requires_onboarding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)

    async def fake_get_profile(_: int, __: object) -> dict[str, object]:
        return {}

    monkeypatch.setattr(
        onboarding_utils.profiles,
        "get_profile_for_user",
        fake_get_profile,
    )
    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, args=["l1"]),
    )
    await learning_handlers.lesson_command(update, context)
    assert message.replies == [onboarding_utils.AGE_PROMPT]


@pytest.mark.asyncio
async def test_learn_reset_deactivates_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal, engine = setup_db()
    monkeypatch.setattr(plans, "SessionLocal", SessionLocal)
    try:
        with SessionLocal() as session:
            session.add(db.User(telegram_id=5, thread_id=""))
            session.commit()
        plan_id = await plans.create_plan(5, version=1, plan_json=[])
        message = DummyMessage()
        update = cast(
            Update,
            SimpleNamespace(message=message, effective_user=SimpleNamespace(id=5)),
        )
        context = cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            SimpleNamespace(user_data={}),
        )
        await learning_onboarding.learn_reset(update, context)
        plan = await plans.get_plan(plan_id)
        assert plan is not None and plan.is_active is False
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_ensure_overrides_logs_http_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def fake_get_profile(_: int, __: object) -> dict[str, object]:
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(
        onboarding_utils.profiles, "get_profile_for_user", fake_get_profile
    )
    user = SimpleNamespace(id=1)
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, callback_query=None, effective_user=user),
    )
    with caplog.at_level(logging.ERROR):
        result = await onboarding_utils.ensure_overrides(update, context)
    assert result is False
    assert message.replies == [onboarding_utils.AGE_PROMPT]
    assert any("Failed to get profile" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_ensure_overrides_propagates_unexpected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_profile(_: int, __: object) -> dict[str, object]:
        raise ValueError("bad")

    monkeypatch.setattr(
        onboarding_utils.profiles, "get_profile_for_user", fake_get_profile
    )
    user = SimpleNamespace(id=1)
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, callback_query=None, effective_user=user),
    )
    with pytest.raises(ValueError):
        await onboarding_utils.ensure_overrides(update, context)


def test_needs_age() -> None:
    assert onboarding_utils.needs_age({})
    assert onboarding_utils.needs_age({"age_group": "adult"}) is False


def test_needs_level() -> None:
    assert onboarding_utils.needs_level({})
    assert onboarding_utils.needs_level({"learning_level": "novice"}) is False
