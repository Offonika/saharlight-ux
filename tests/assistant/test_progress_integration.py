from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.config import settings
from services.api.app.diabetes import curriculum_engine
from services.api.app.diabetes.models_learning import Lesson
from services.api.app.diabetes.services import db, gpt_client
from services.api.app.assistant.services import progress_service


@pytest.fixture(autouse=True)
def setup_db(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(progress_service, "SessionLocal", SessionLocal, raising=False)
    db.Base.metadata.create_all(bind=engine)
    yield
    db.dispose_engine(engine)


@pytest.mark.asyncio()
async def test_progress_saved_each_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        lesson = Lesson(slug="intro", title="Intro", content="desc")
        session.add(lesson)
        session.commit()
        lesson_id = lesson.id
        slug = lesson.slug

    async def fake_completion(**kwargs: object) -> str:  # noqa: ANN401 - test stub
        return "text"

    monkeypatch.setattr(
        gpt_client, "create_learning_chat_completion", fake_completion
    )

    await curriculum_engine.start_lesson(1, slug)

    await curriculum_engine.next_step(1, lesson_id, {})
    progress1 = await progress_service.get_progress(1, slug)
    assert progress1 is not None
    assert progress1.step == 1

    await curriculum_engine.next_step(1, lesson_id, {})
    progress2 = await progress_service.get_progress(1, slug)
    assert progress2 is not None
    assert progress2.step == 2

