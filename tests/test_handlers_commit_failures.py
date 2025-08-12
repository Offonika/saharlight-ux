import datetime
import json
import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from telegram.ext import ConversationHandler
import services.api.app.diabetes.handlers.profile_handlers as profile_handlers
import services.api.app.diabetes.handlers.common_handlers as common_handlers
import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers


class DummyMessage:
    def __init__(self):
        self.texts: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)


class DummyQuery:
    def __init__(self, data: str):
        self.data = data
        self.edited = []

    async def answer(self, *args, **kwargs):
        pass

    async def edit_message_text(self, text, **kwargs):
        self.edited.append(text)


class DummyWebAppMessage(DummyMessage):
    def __init__(self, data: str):
        super().__init__()
        self.web_app_data = SimpleNamespace(data=data)


@pytest.mark.asyncio
async def test_profile_command_no_local_session(monkeypatch):
    """Profile command should not touch the local DB session."""
    import os

    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401

    session_factory = MagicMock()
    monkeypatch.setattr(profile_handlers, "SessionLocal", session_factory)

    dummy_api = SimpleNamespace(profiles_post=MagicMock())
    monkeypatch.setattr(
        profile_handlers, "_get_api", lambda: (dummy_api, Exception, MagicMock)
    )

    message = DummyMessage()
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(args=["10", "2", "6", "4", "9"], user_data={})

    result = await profile_handlers.profile_command(update, context)

    assert not session_factory.called
    assert message.texts[0].startswith("✅ Профиль обновлён")
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_callback_router_commit_failure(monkeypatch, caplog):
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

    monkeypatch.setattr(common_handlers, "SessionLocal", lambda: session)

    pending_entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    query = DummyQuery("confirm_entry")
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={"pending_entry": pending_entry})

    with caplog.at_level(logging.ERROR):
        await common_handlers.callback_router(update, context)

    assert session.rollback.called
    assert "DB commit failed" in caplog.text
    assert query.edited == ["⚠️ Не удалось сохранить запись."]


@pytest.mark.asyncio
async def test_add_reminder_commit_failure(monkeypatch, caplog):
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
    schedule_mock = MagicMock()
    monkeypatch.setattr(reminder_handlers, "schedule_reminder", schedule_mock)

    message = DummyMessage()
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(
        args=["sugar", "23:00"],
        job_queue=SimpleNamespace(get_jobs_by_name=lambda name: []),
    )

    with caplog.at_level(logging.ERROR):
        await reminder_handlers.add_reminder(update, context)

    assert session.rollback.called
    assert "DB commit failed" in caplog.text
    assert message.texts == ["⚠️ Не удалось сохранить напоминание."]
    assert not schedule_mock.called


@pytest.mark.asyncio
async def test_reminder_webapp_save_commit_failure(monkeypatch, caplog):
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    rem = SimpleNamespace(
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
    update = SimpleNamespace(
        effective_message=message, effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(job_queue=SimpleNamespace())

    with caplog.at_level(logging.ERROR):
        await reminder_handlers.reminder_webapp_save(update, context)

    assert session.rollback.called
    assert not session.refresh.called
    assert not schedule_mock.called
    assert not render_mock.called
    assert message.texts == ["⚠️ Не удалось сохранить напоминание."]
    assert "Failed to commit reminder via webapp" in caplog.text


@pytest.mark.asyncio
async def test_delete_reminder_commit_failure(monkeypatch, caplog):
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    session.commit.side_effect = SQLAlchemyError("fail")
    session.rollback = MagicMock()
    rem = SimpleNamespace(id=1, telegram_id=1)
    session.get.return_value = rem

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: session)

    job_queue = SimpleNamespace(get_jobs_by_name=MagicMock())
    message = DummyMessage()
    update = SimpleNamespace(message=message)
    context = SimpleNamespace(args=["1"], job_queue=job_queue)

    with caplog.at_level(logging.ERROR):
        await reminder_handlers.delete_reminder(update, context)

    assert session.rollback.called
    assert message.texts == ["⚠️ Не удалось удалить напоминание."]
    assert not job_queue.get_jobs_by_name.called
    assert "Failed to commit reminder deletion" in caplog.text


@pytest.mark.asyncio
async def test_reminder_job_commit_failure(monkeypatch, caplog):
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    rem = SimpleNamespace(id=1, telegram_id=1, is_enabled=True)
    session.get.side_effect = [rem]
    session.add = MagicMock()
    session.commit.side_effect = SQLAlchemyError("fail")
    session.rollback = MagicMock()

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: session)
    describe_mock = MagicMock()
    monkeypatch.setattr(reminder_handlers, "_describe", describe_mock)

    context = SimpleNamespace(
        job=SimpleNamespace(data={"reminder_id": 1, "chat_id": 1}),
        bot=SimpleNamespace(send_message=MagicMock()),
    )

    with caplog.at_level(logging.ERROR):
        await reminder_handlers.reminder_job(context)

    assert session.rollback.called
    assert session.get.call_count == 1
    assert not describe_mock.called
    assert not context.bot.send_message.called
    assert "Failed to log reminder trigger for reminder 1" in caplog.text


@pytest.mark.asyncio
async def test_reminder_callback_commit_failure(monkeypatch, caplog):
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    session.add = MagicMock()
    session.commit.side_effect = SQLAlchemyError("fail")
    session.rollback = MagicMock()
    session.get.return_value = SimpleNamespace(id=1, telegram_id=1)

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: session)
    reminder_handlers.commit_session = common_handlers.commit_session

    query = DummyQuery("remind_snooze:1")
    update = SimpleNamespace(
        callback_query=query, effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(job_queue=SimpleNamespace(run_once=MagicMock()))

    with caplog.at_level(logging.ERROR):
        await reminder_handlers.reminder_callback(update, context)

    assert session.rollback.called
    assert query.edited == []
    assert not context.job_queue.run_once.called
    assert "Failed to log reminder action remind_snooze for reminder 1" in caplog.text


@pytest.mark.asyncio
async def test_reminder_action_cb_commit_failure(monkeypatch, caplog):
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    rem = SimpleNamespace(id=1, telegram_id=1, is_enabled=True)
    session.get.return_value = rem
    session.commit.side_effect = SQLAlchemyError("fail")
    session.rollback = MagicMock()
    session.refresh = MagicMock()

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: session)
    schedule_mock = MagicMock()
    monkeypatch.setattr(reminder_handlers, "schedule_reminder", schedule_mock)

    job_queue = SimpleNamespace(get_jobs_by_name=MagicMock())
    query = DummyQuery("rem_toggle:1")
    update = SimpleNamespace(
        callback_query=query, effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(job_queue=job_queue)

    with caplog.at_level(logging.ERROR):
        await reminder_handlers.reminder_action_cb(update, context)

    assert session.rollback.called
    assert not schedule_mock.called
    assert not job_queue.get_jobs_by_name.called
    assert query.edited == []
    assert "Failed to commit reminder action toggle for reminder 1" in caplog.text
