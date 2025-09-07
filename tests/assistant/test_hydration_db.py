from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from telegram import Bot, Chat, Message, Update, User
from telegram.ext import Application, MessageHandler, filters

from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.services import db
from services.api.app.diabetes.models_learning import Lesson, LessonLog, LessonProgress, User as DbUser


class DummyBot(Bot):
    """Bot collecting sent texts for assertions."""

    def __init__(self) -> None:  # pragma: no cover - simple setup
        super().__init__(token="123:ABC")
        object.__setattr__(self, "_sent", [])

    @property
    def sent(self) -> list[str]:  # pragma: no cover - simple property
        return self._sent  # type: ignore[attr-defined]

    async def initialize(self) -> None:  # pragma: no cover - setup
        self._me = User(id=0, is_bot=True, first_name="Bot", username="bot")  # type: ignore[attr-defined]
        self._bot = self
        self._initialized = True

    @property
    def username(self) -> str:  # pragma: no cover - simple property
        return "bot"

    async def send_message(self, chat_id: int, text: str, **kwargs: Any) -> Message:
        msg = Message(
            message_id=len(self.sent) + 1,
            date=datetime.now(),
            chat=Chat(id=chat_id, type="private"),
            from_user=self._me,
            text=text,
        )
        msg._bot = self
        self.sent.append(text)
        return msg


@pytest.fixture(autouse=True)
def setup_db() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    learning_handlers.SessionLocal = db.SessionLocal  # type: ignore[assignment]
    yield
    db.dispose_engine(engine)


@pytest.mark.asyncio()
async def test_hydration_from_db(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = DummyBot()
    app = Application.builder().bot(bot).build()
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, learning_handlers.on_any_text)
    )
    await app.initialize()

    user_id = 1
    with db.SessionLocal() as session:
        user = DbUser(telegram_id=user_id, thread_id="t1")
        lesson = Lesson(slug="t1", title="Intro", content="c")
        session.add_all([user, lesson])
        session.commit()
        progress = LessonProgress(
            user_id=user_id, lesson_id=lesson.id, current_step=3, completed=False
        )
        log = LessonLog(
            telegram_id=user_id,
            topic_slug="t1",
            role="assistant",
            step_idx=3,
            content="snapshot",
        )
        session.add_all([progress, log])
        session.commit()

    called: dict[str, Any] = {}

    async def fake_lesson_answer_handler(update: Update, context: Any) -> None:
        state = learning_handlers.get_state(context.user_data)
        called["state"] = state

    monkeypatch.setattr(learning_handlers, "lesson_answer_handler", fake_lesson_answer_handler)

    user = User(id=user_id, is_bot=False, first_name="T")
    chat = Chat(id=1, type="private")
    msg = Message(
        message_id=1,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text="answer",
    )
    msg._bot = bot

    await app.process_update(Update(update_id=1, message=msg))

    assert "state" in called
    state = called["state"]
    assert state.topic == "t1"
    assert state.step == 3
    assert state.last_step_text == "snapshot"
    data = app.user_data[user_id]
    assert data["learning_module_idx"] == 0
    assert data["learning_plan_index"] == 2
    assert data["learning_plan"][0] == "snapshot"

    await app.shutdown()
