import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers as dynamic_handlers
from services.api.app.diabetes import learning_onboarding as onboarding_utils
from services.api.app.diabetes.handlers import learning_handlers as legacy_handlers
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.services import db
from services.api.app.ui.keyboard import LEARN_BUTTON_TEXT


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(
        self, text: str, **kwargs: Any
    ) -> None:  # pragma: no cover - helper
        self.replies.append(text)


class DummyCallback:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data
        self.answered = False

    async def answer(self) -> None:  # pragma: no cover - helper
        self.answered = True


@pytest.mark.asyncio
async def test_learn_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=None))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await legacy_handlers.learn_command(update, context)
    assert message.replies == [f"🚫 {LEARN_BUTTON_TEXT} недоступен."]


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    return SessionLocal


@pytest.mark.asyncio
async def test_learn_enabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_command_model", "super-model")
    monkeypatch.setattr(settings, "learning_content_mode", "static")
    sample = [
        {
            "title": "Sample",
            "steps": ["s1"],
            "quiz": [{"question": "q1", "options": ["1", "2", "3"], "answer": 1}],
        }
    ]
    path = tmp_path / "lessons.json"
    path.write_text(json.dumps(sample), encoding="utf-8")
    SessionLocal = setup_db()
    await load_lessons(path, sessionmaker=SessionLocal)
    monkeypatch.setattr(legacy_handlers, "SessionLocal", SessionLocal)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=None))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data={
                "learning_onboarded": True,
                "learn_profile_overrides": {
                    "age_group": "adult",
                    "diabetes_type": "T1",
                    "learning_level": "novice",
                },
            }
        ),
    )
    await legacy_handlers.learn_command(update, context)
    assert "super-model" in message.replies[0]


@pytest.mark.asyncio
async def test_dynamic_learn_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = SimpleNamespace(user_data={}, args=[])
    await dynamic_handlers.learn_command(update, context)
    assert message.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_dynamic_lesson_command_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = SimpleNamespace(user_data={}, args=["slug"])
    await dynamic_handlers.lesson_command(update, context)
    assert message.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_dynamic_lesson_callback_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    query = DummyCallback(message, "lesson:slug")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = SimpleNamespace(user_data={})
    await dynamic_handlers.lesson_callback(update, context)
    assert message.replies == ["режим обучения отключён"]
    assert query.answered is True


@pytest.mark.asyncio
async def test_dynamic_lesson_answer_handler_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage(text="ans")
    update = cast(Update, SimpleNamespace(message=message))
    context = SimpleNamespace(user_data={})
    await dynamic_handlers.lesson_answer_handler(update, context)
    assert message.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_dynamic_exit_command_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = SimpleNamespace(user_data={})
    await dynamic_handlers.exit_command(update, context)
    assert message.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_plan_precedes_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_hydrate(*args: object, **kwargs: object) -> bool:
        return True

    async def fake_get_profile(_: int, __: object) -> dict[str, object]:
        return {}

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        return ("first", False)

    async def fake_add_log(*_: object, **__: object) -> None:
        return None

    async def fake_persist(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(dynamic_handlers, "_hydrate", fake_hydrate)
    monkeypatch.setattr(
        dynamic_handlers.profiles,
        "get_profile_for_user",
        fake_get_profile,
    )
    monkeypatch.setattr(
        onboarding_utils.profiles,
        "get_profile_for_user",
        fake_get_profile,
    )
    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine,
        "start_lesson",
        fake_start_lesson,
    )
    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine,
        "next_step",
        fake_next_step,
    )
    monkeypatch.setattr(dynamic_handlers, "choose_initial_topic", lambda _: ("slug", "t"))
    monkeypatch.setattr(
        dynamic_handlers,
        "generate_learning_plan",
        lambda _: ["first", "second"],
    )
    monkeypatch.setattr(dynamic_handlers, "pretty_plan", lambda p: "|".join(p))
    monkeypatch.setattr(dynamic_handlers, "format_reply", lambda t: t)
    monkeypatch.setattr(dynamic_handlers, "safe_add_lesson_log", fake_add_log)
    monkeypatch.setattr(dynamic_handlers, "_persist", fake_persist)

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data={
                "learning_onboarded": True,
                "learn_profile_overrides": {
                    "age_group": "adult",
                    "learning_level": "novice",
                },
            },
            bot_data={},
        ),
    )

    await dynamic_handlers.learn_command(update, context)
    assert message.replies == [
        "\U0001f5fa План обучения\nfirst|second",
        "first",
    ]


@pytest.mark.asyncio
async def test_reenter_after_onboarding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    counts = {"start": 0, "next": 0}

    async def fake_hydrate(*args: object, **kwargs: object) -> bool:
        return True

    async def fake_get_profile(_: int, __: object) -> dict[str, object]:
        return {}

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        counts["start"] += 1
        return SimpleNamespace(lesson_id=1)

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        counts["next"] += 1
        return ("first", False)

    async def fake_add_log(*_: object, **__: object) -> None:
        return None

    async def fake_persist(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(dynamic_handlers, "_hydrate", fake_hydrate)
    monkeypatch.setattr(
        dynamic_handlers.profiles,
        "get_profile_for_user",
        fake_get_profile,
    )
    monkeypatch.setattr(
        onboarding_utils.profiles,
        "get_profile_for_user",
        fake_get_profile,
    )
    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine,
        "start_lesson",
        fake_start_lesson,
    )
    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine,
        "next_step",
        fake_next_step,
    )
    monkeypatch.setattr(dynamic_handlers, "choose_initial_topic", lambda _: ("slug", "t"))
    monkeypatch.setattr(
        dynamic_handlers,
        "generate_learning_plan",
        lambda _: ["first", "second"],
    )
    monkeypatch.setattr(dynamic_handlers, "pretty_plan", lambda p: "|".join(p))
    monkeypatch.setattr(dynamic_handlers, "format_reply", lambda t: t)
    monkeypatch.setattr(dynamic_handlers, "safe_add_lesson_log", fake_add_log)
    monkeypatch.setattr(dynamic_handlers, "_persist", fake_persist)

    user_data: dict[str, Any] = {
        "learning_onboarded": True,
        "learn_profile_overrides": {
            "age_group": "adult",
            "learning_level": "novice",
        },
    }
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data, bot_data={}),
    )

    msg1 = DummyMessage()
    upd1 = cast(
        Update, SimpleNamespace(message=msg1, effective_user=SimpleNamespace(id=1))
    )
    await dynamic_handlers.learn_command(upd1, context)
    assert msg1.replies == [
        "\U0001f5fa План обучения\nfirst|second",
        "first",
    ]

    msg2 = DummyMessage()
    upd2 = cast(
        Update, SimpleNamespace(message=msg2, effective_user=SimpleNamespace(id=1))
    )
    await dynamic_handlers.learn_command(upd2, context)
    assert msg2.replies == ["first"]
    assert counts == {"start": 1, "next": 1}
    assert user_data["learning_plan"] == ["first", "second"]
    assert user_data["learning_plan_index"] == 0
    assert "diabetes_type" not in user_data["learn_profile_overrides"]
