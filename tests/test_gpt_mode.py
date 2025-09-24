from types import SimpleNamespace
from typing import Any, NoReturn, cast
from unittest.mock import AsyncMock

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes import assistant_state
from services.api.app.diabetes.handlers import assistant_menu, gpt_handlers, registration


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[str] = []
        self.edits: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:
        self.replies.append(text)

    async def edit_text(self, text: str, **_: Any) -> None:
        self.edits.append(text)


class DummyJob:
    def __init__(self, name: str, data: object | None) -> None:
        self.name = name
        self.data = data
        self.removed = False

    def schedule_removal(self) -> None:
        self.removed = True


class DummyJobQueue:
    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [job for job in self.jobs if job.name == name]

    def run_once(
        self,
        _callback: object,
        when: object | None = None,
        *,
        name: str | None = None,
        data: object | None = None,
        **_: object,
    ) -> DummyJob:
        job = DummyJob(name or "", data)
        self.jobs.append(job)
        return job


class DummyCallbackQuery:
    def __init__(self, data: str, message: DummyMessage) -> None:
        self.data = data
        self.message = message
        self.answered = False

    async def answer(self) -> None:
        self.answered = True


def make_update(message: DummyMessage) -> Update:
    return cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))


def make_context(
    user_data: dict[str, Any] | None = None,
    *,
    job_queue: DummyJobQueue | None = None,
) -> CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    return cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data=user_data if user_data is not None else {},
            job_queue=job_queue,
        ),
    )


def forbid_parse_quick_values(*_: object, **__: object) -> NoReturn:
    raise AssertionError("parse_quick_values should not be called")


@pytest.mark.asyncio
async def test_start_gpt_sets_flag() -> None:
    message = DummyMessage("/gpt")
    update = make_update(message)
    context = make_context({})
    await registration.start_gpt_dialog(update, context)
    assert context.user_data.get(registration.GPT_MODE_KEY) is True
    assert registration.MODE_DISCLAIMED_KEY not in context.user_data


@pytest.mark.asyncio
async def test_cancel_clears_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("/cancel")
    update = make_update(message)
    user_data = {registration.GPT_MODE_KEY: True, registration.MODE_DISCLAIMED_KEY: True}
    fake_cancel = AsyncMock()
    monkeypatch.setattr("services.api.app.diabetes.handlers.dose_calc.dose_cancel", fake_cancel)
    context = make_context(user_data)
    await registration.cancel(update, context)
    assert registration.GPT_MODE_KEY not in user_data
    assert registration.MODE_DISCLAIMED_KEY not in user_data
    fake_cancel.assert_awaited_once()


@pytest.mark.asyncio
async def test_freeform_routes_to_gpt(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("hello")
    update = make_update(message)
    context = make_context({registration.GPT_MODE_KEY: True})
    chat_called = AsyncMock()
    monkeypatch.setattr(gpt_handlers, "chat_with_gpt", chat_called)

    def fail_parse(*args: object, **kwargs: object) -> None:
        raise AssertionError("parse_quick_values should not be called")

    monkeypatch.setattr(gpt_handlers, "parse_quick_values", fail_parse)
    await gpt_handlers.freeform_handler(update, context)
    chat_called.assert_awaited_once()


@pytest.mark.asyncio
async def test_assistant_menu_chat_enables_gpt_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    job_queue = DummyJobQueue()
    user_data: dict[str, Any] = {}
    message = DummyMessage("menu")
    query = DummyCallbackQuery("asst:chat", message)
    update = cast(
        Update,
        SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1)),
    )
    memory_set = AsyncMock()
    monkeypatch.setattr(assistant_menu.memory_service, "set_last_mode", memory_set)
    context = make_context(user_data, job_queue=job_queue)

    await assistant_menu.assistant_callback(update, context)

    assert user_data.get(registration.GPT_MODE_KEY) is True
    assert registration.MODE_DISCLAIMED_KEY not in user_data
    assert job_queue.jobs and job_queue.jobs[0].name == "gpt_timeout_1"
    assert job_queue.jobs[0].data == 1
    assert message.replies and message.replies[-1].startswith("💬 GPT режим")
    memory_set.assert_awaited_once_with(1, "chat")

    chat_called = AsyncMock()
    monkeypatch.setattr(gpt_handlers, "chat_with_gpt", chat_called)

    async def fake_parse_via_gpt(
        raw_text: str,
        _message: DummyMessage,
        *,
        parse_command: object,
        on_unrecognized: Any = None,
    ) -> None:
        assert raw_text == "Привет"
        if on_unrecognized is not None:
            await on_unrecognized()
        return None

    monkeypatch.setattr(gpt_handlers, "parse_via_gpt", fake_parse_via_gpt)
    monkeypatch.setattr(gpt_handlers, "parse_quick_values", forbid_parse_quick_values)

    chat_message = DummyMessage("Привет")
    chat_update = make_update(chat_message)
    chat_context = make_context(user_data, job_queue=job_queue)

    await gpt_handlers.freeform_handler(chat_update, chat_context)
    chat_called.assert_awaited_once()


@pytest.mark.asyncio
async def test_assistant_menu_chat_reschedules_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    job_queue = DummyJobQueue()
    user_data: dict[str, Any] = {}
    memory_set = AsyncMock()
    monkeypatch.setattr(assistant_menu.memory_service, "set_last_mode", memory_set)

    first_message = DummyMessage("menu")
    first_query = DummyCallbackQuery("asst:chat", first_message)
    first_update = cast(
        Update,
        SimpleNamespace(callback_query=first_query, effective_user=SimpleNamespace(id=1)),
    )
    await assistant_menu.assistant_callback(first_update, make_context(user_data, job_queue=job_queue))
    first_job = job_queue.jobs[0]

    second_message = DummyMessage("menu")
    second_query = DummyCallbackQuery("asst:chat", second_message)
    second_update = cast(
        Update,
        SimpleNamespace(callback_query=second_query, effective_user=SimpleNamespace(id=1)),
    )
    await assistant_menu.assistant_callback(second_update, make_context(user_data, job_queue=job_queue))

    assert first_job.removed is True
    assert len(job_queue.jobs) == 2
    assert job_queue.jobs[1].name == "gpt_timeout_1"
    assert job_queue.jobs[1].data == 1


@pytest.mark.asyncio
async def test_freeform_chat_fallback_on_non_add_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("Привет")
    update = make_update(message)
    user_data = {assistant_state.LAST_MODE_KEY: "chat"}
    context = make_context(user_data)

    chat_called = AsyncMock()
    monkeypatch.setattr(gpt_handlers, "chat_with_gpt", chat_called)

    async def fake_parse_command(_: str) -> dict[str, object]:
        return {"action": "get_day_summary"}

    monkeypatch.setattr(gpt_handlers, "parse_command", fake_parse_command)
    monkeypatch.setattr(gpt_handlers, "parse_quick_values", forbid_parse_quick_values)

    await gpt_handlers.freeform_handler(update, context)

    chat_called.assert_awaited_once()
    assert message.replies == []
