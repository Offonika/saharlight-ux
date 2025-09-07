from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes import learning_onboarding as onboarding_utils
from services.api.app.diabetes.handlers import learning_handlers, learning_onboarding
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.services import db


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(
        self, text: str, **kwargs: Any
    ) -> None:  # pragma: no cover - helper
        self.replies.append(text)


class DummyCallbackQuery:
    def __init__(self, data: str, message: DummyMessage) -> None:
        self.data = data
        self.message = message
        self.answers: list[str | None] = []

    async def answer(self, text: str | None = None, **kwargs: Any) -> None:  # pragma: no cover - helper
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

        message2 = DummyMessage("adult")
        update2 = cast(Update, SimpleNamespace(message=message2, effective_user=None))
        await learning_onboarding.onboarding_reply(update2, context)
        assert message2.replies == [onboarding_utils.DIABETES_TYPE_PROMPT]

        message3 = DummyMessage("type1")
        update3 = cast(Update, SimpleNamespace(message=message3, effective_user=None))
        await learning_onboarding.onboarding_reply(update3, context)
        assert message3.replies == [onboarding_utils.LEARNING_LEVEL_PROMPT]

        message4 = DummyMessage("beginner")
        update4 = cast(Update, SimpleNamespace(message=message4, effective_user=None))
        await learning_onboarding.onboarding_reply(update4, context)
        assert message4.replies == [
            "Ответы сохранены. Отправьте /learn чтобы продолжить."
        ]
        assert context.user_data["learn_profile_overrides"] == {
            "age_group": "adult",
            "diabetes_type": "T1",
            "learning_level": "novice",
        }

        message5 = DummyMessage()
        update5 = cast(Update, SimpleNamespace(message=message5, effective_user=None))
        await learning_handlers.learn_command(update5, context)
        assert any(
            "Учебный режим" in text or "Урок" in text for text in message5.replies
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
        assert q1_msg.replies == [onboarding_utils.DIABETES_TYPE_PROMPT]

        q2_msg = DummyMessage()
        q2 = DummyCallbackQuery(f"{onboarding_utils.CB_PREFIX}T1", q2_msg)
        upd_cb2 = cast(
            Update,
            SimpleNamespace(callback_query=q2, message=None, effective_user=None),
        )
        await learning_onboarding.onboarding_callback(upd_cb2, ctx)
        assert q2_msg.replies == [onboarding_utils.LEARNING_LEVEL_PROMPT]

        q3_msg = DummyMessage()
        q3 = DummyCallbackQuery(f"{onboarding_utils.CB_PREFIX}novice", q3_msg)
        upd_cb3 = cast(
            Update,
            SimpleNamespace(callback_query=q3, message=None, effective_user=None),
        )
        await learning_onboarding.onboarding_callback(upd_cb3, ctx)
        assert q3_msg.replies == [
            "Ответы сохранены. Отправьте /learn чтобы продолжить.",
        ]
        assert ctx.user_data["learn_profile_overrides"] == {
            "age_group": "adult",
            "diabetes_type": "T1",
            "learning_level": "novice",
        }

        msg2 = DummyMessage()
        upd2 = cast(Update, SimpleNamespace(message=msg2, effective_user=None))
        await learning_handlers.learn_command(upd2, ctx)
        assert any(
            "Учебный режим" in text or "Урок" in text for text in msg2.replies
        )
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
async def test_lesson_command_requires_onboarding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
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
