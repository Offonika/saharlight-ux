import datetime
import json
import logging
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from telegram import Bot, Update, User
from telegram.ext import CallbackContext, ConversationHandler, Job, JobQueue
from services.api.app.diabetes.handlers import profile as profile_handlers
import services.api.app.diabetes.handlers.router as router
from services.api.app.diabetes.services.repository import commit
import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.data = data
        self.message = message
        self.edited: list[str] = []


    async def answer(self, text: str | None = None, **kwargs: Any) -> None:

        pass

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edited.append(text)


class DummyWebAppMessage(DummyMessage):
    def __init__(self, data: str) -> None:
        super().__init__()
        self.web_app_data = DummyWebAppData(data)


class DummyWebAppData:
    def __init__(self, data: str) -> None:
        self.data = data


@dataclass
class ReminderStub:
    id: int = 1
    telegram_id: int = 1
    is_enabled: bool | None = None
    type: str | None = None
    time: datetime.time | None = None
    interval_hours: int | None = None
    minutes_after: int | None = None


def make_user(user_id: int) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    return user


def make_update(**kwargs: Any) -> MagicMock:
    update = MagicMock(spec=Update)
    for key, value in kwargs.items():
        setattr(update, key, value)
    return update


def make_context(**kwargs: Any) -> MagicMock:
    context = MagicMock(spec=CallbackContext)
    for key, value in kwargs.items():
        setattr(context, key, value)
    return context


@pytest.mark.asyncio
async def test_profile_command_no_local_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Profile command should not touch the local DB session."""
    import os

    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401

    session_factory = MagicMock()
    monkeypatch.setattr(profile_handlers, "SessionLocal", session_factory)

    dummy_api = MagicMock()
    dummy_api.profiles_post = MagicMock()
    monkeypatch.setattr(
        profile_handlers, "get_api", lambda: (dummy_api, Exception, MagicMock)
    )

    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["10", "2", "6", "4", "9"], user_data={})

    result = await profile_handlers.profile_command(update, context)

    assert not session_factory.called
    assert message.texts[0].startswith("✅ Профиль обновлён")
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_callback_router_commit_failure(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    import os

    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401

    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    session.add = MagicMock()
    session.commit.side_effect = SQLAlchemyError("fail")
    session.rollback = MagicMock()
    rem = ReminderStub(id=1, telegram_id=1)
    session.get.return_value = rem

    monkeypatch.setattr(router, "SessionLocal", lambda: session)

    pending_entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    query = DummyQuery(DummyMessage(), "confirm_entry")
    update = make_update(callback_query=query)
    context = make_context(user_data={"pending_entry": pending_entry})

    with caplog.at_level(logging.ERROR):
        await router.callback_router(update, context)

    assert session.rollback.called
    assert "DB commit failed" in caplog.text
    assert query.edited == ["⚠️ Не удалось сохранить запись."]
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.asyncio
async def test_add_reminder_commit_failure(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    session.add = MagicMock()
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.count.return_value = 0
    query_mock.filter_by.return_value = filter_mock
    session.query.return_value = query_mock
    session.commit.side_effect = SQLAlchemyError("fail")
    session.rollback = MagicMock()

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: session)
    monkeypatch.setattr(reminder_handlers, "commit", commit)
    schedule_mock = MagicMock()
    monkeypatch.setattr(reminder_handlers, "schedule_reminder", schedule_mock)

    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    job_queue = MagicMock(spec=JobQueue)
    job_queue.get_jobs_by_name.return_value = []
    context = make_context(args=["sugar", "23:00"], job_queue=job_queue)

    with caplog.at_level(logging.ERROR):
        await reminder_handlers.add_reminder(update, context)

    assert session.rollback.called
    assert "DB commit failed" in caplog.text
    assert message.texts == ["⚠️ Не удалось сохранить напоминание."]
    assert not schedule_mock.called
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.asyncio
async def test_reminder_webapp_save_commit_failure(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    rem = ReminderStub(
        telegram_id=1,
        type="sugar",
        is_enabled=True,
        time=None,
        interval_hours=None,
        minutes_after=None,
    )
    session.get.return_value = rem
    session.commit.side_effect = SQLAlchemyError("fail")
    session.rollback = MagicMock()
    session.refresh = MagicMock()

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: session)
    schedule_mock = MagicMock()
    monkeypatch.setattr(reminder_handlers, "schedule_reminder", schedule_mock)
    render_mock = MagicMock()
    monkeypatch.setattr(reminder_handlers, "_render_reminders", render_mock)

    message = DummyWebAppMessage(
        json.dumps({"type": "sugar", "value": "23:00", "id": 1})
    )
    update = make_update(effective_message=message, effective_user=make_user(1))
    context = make_context(job_queue=MagicMock(spec=JobQueue))

    with caplog.at_level(logging.ERROR):
        await reminder_handlers.reminder_webapp_save(update, context)

    assert session.rollback.called
    assert not session.refresh.called
    assert not schedule_mock.called
    assert not render_mock.called
    assert message.texts == ["⚠️ Не удалось сохранить напоминание."]
    assert "Failed to commit reminder via webapp" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.asyncio
async def test_delete_reminder_commit_failure(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    session.commit.side_effect = SQLAlchemyError("fail")
    session.rollback = MagicMock()
    rem = ReminderStub(id=1, telegram_id=1)
    session.get.return_value = rem

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: session)

    job_queue = MagicMock(spec=JobQueue)
    job_queue.get_jobs_by_name = MagicMock()
    message = DummyMessage()
    update = make_update(message=message)
    context = make_context(args=["1"], job_queue=job_queue)

    with caplog.at_level(logging.ERROR):
        await reminder_handlers.delete_reminder(update, context)

    assert session.rollback.called
    assert message.texts == ["⚠️ Не удалось удалить напоминание."]
    assert not job_queue.get_jobs_by_name.called
    assert "Failed to commit reminder deletion" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.asyncio
async def test_reminder_job_commit_failure(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    rem = ReminderStub(id=1, telegram_id=1, is_enabled=True)
    session.get.side_effect = [rem]
    session.add = MagicMock()
    session.commit.side_effect = SQLAlchemyError("fail")
    session.rollback = MagicMock()

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: session)
    describe_mock = MagicMock()
    monkeypatch.setattr(reminder_handlers, "_describe", describe_mock)

    job = MagicMock(spec=Job)
    job.data = {"reminder_id": 1, "chat_id": 1}
    bot = MagicMock(spec=Bot)
    bot.send_message = MagicMock()
    context = make_context(job=job, bot=bot)

    with caplog.at_level(logging.ERROR):
        await reminder_handlers.reminder_job(context)

    assert session.rollback.called
    assert session.get.call_count == 1
    assert not describe_mock.called
    assert not context.bot.send_message.called
    assert "Failed to log reminder trigger for reminder 1" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.asyncio
async def test_reminder_callback_commit_failure(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    session.add = MagicMock()
    session.rollback = MagicMock()

    rem = ReminderStub(id=1, telegram_id=1)
    session.get.return_value = rem

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: session)
    reminder_handlers.commit = commit

    def failing_commit(sess: Session) -> bool:
        sess.rollback()
        return False

    monkeypatch.setattr(reminder_handlers, "commit", failing_commit)

    query = DummyQuery(DummyMessage(), "remind_snooze:1")
    update = make_update(callback_query=query, effective_user=make_user(1))
    job_queue = MagicMock(spec=JobQueue)
    job_queue.run_once = MagicMock()
    context = make_context(job_queue=job_queue)

    with caplog.at_level(logging.ERROR):
        await reminder_handlers.reminder_callback(update, context)

    assert session.rollback.called
    assert query.edited == []
    assert not context.job_queue.run_once.called
    assert "Failed to log reminder action remind_snooze for reminder 1" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.asyncio
async def test_reminder_action_cb_commit_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    rem = ReminderStub(id=1, telegram_id=1, is_enabled=True)
    session.get.return_value = rem
    session.commit.side_effect = SQLAlchemyError("fail")
    session.rollback = MagicMock()
    session.refresh = MagicMock()

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: session)
    schedule_mock = MagicMock()
    monkeypatch.setattr(reminder_handlers, "schedule_reminder", schedule_mock)

    job_queue = MagicMock(spec=JobQueue)
    job_queue.get_jobs_by_name = MagicMock()
    query = DummyQuery(DummyMessage(), "rem_toggle:1")
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = make_context(job_queue=job_queue)

    with caplog.at_level(logging.ERROR):
        await reminder_handlers.reminder_action_cb(update, context)

    assert session.rollback.called
    assert not schedule_mock.called
    assert not job_queue.get_jobs_by_name.called
    assert query.edited == []
    assert "Failed to commit reminder action toggle for reminder 1" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)
