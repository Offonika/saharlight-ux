from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app import config
from services.api.app.ui.keyboard import LEARN_BUTTON_TEXT
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.handlers import learning_handlers
from services.api.app.diabetes.services import db


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    return SessionLocal


@pytest.mark.asyncio()
async def test_learning_mode_enabled_lists_lessons(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sample = [
        {
            "title": "Sample",
            "steps": ["a"],
            "quiz": [{"question": "q1", "options": ["1", "2"], "answer": 1}],
        }
    ]
    path = tmp_path / "lessons.json"
    path.write_text(json.dumps(sample), encoding="utf-8")

    monkeypatch.setenv("LEARNING_MODE_ENABLED", "true")
    monkeypatch.setenv("LEARNING_ENABLED", "1")
    monkeypatch.setenv("LEARNING_CONTENT_MODE", "static")
    settings = config.reload_settings()

    SessionLocal = setup_db()
    import services.api.app.diabetes.learning_fixtures as lf

    monkeypatch.setattr(lf, "init_db", lambda: None)
    monkeypatch.setattr(
        lf,
        "load_lessons",
        lambda p: load_lessons(p, sessionmaker=SessionLocal),
    )
    with caplog.at_level(logging.INFO, logger=lf.__name__):
        await lf.main([str(path)])
    assert "OK: lessons loaded" in caplog.text
    caplog.clear()

    monkeypatch.setattr(learning_handlers, "SessionLocal", SessionLocal)
    monkeypatch.setattr(learning_handlers, "settings", settings)

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

    await learning_handlers.learn_command(update, context)

    assert message.replies[0].startswith(f"{LEARN_BUTTON_TEXT} активирован.")
    keyboard = message.kwargs[0].get("reply_markup")
    assert keyboard is not None
    assert keyboard.keyboard


@pytest.mark.asyncio()
async def test_learning_mode_disabled_denies_access(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("LEARNING_MODE_ENABLED", "false")
    monkeypatch.setenv("LEARNING_ENABLED", "0")
    monkeypatch.setenv("LEARNING_CONTENT_MODE", "static")
    settings = config.reload_settings()
    monkeypatch.setattr(learning_handlers, "settings", settings)

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

    with caplog.at_level(
        logging.INFO, logger="services.api.app.diabetes.learning_fixtures"
    ):
        await learning_handlers.learn_command(update, context)

    assert message.replies == [f"🚫 {LEARN_BUTTON_TEXT} недоступен."]
    assert "OK: lessons loaded" not in caplog.text
