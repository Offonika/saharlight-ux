import os
import builtins
import logging
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    JobQueue,
    MessageHandler,
)
from services.api.app.diabetes.handlers.callbackquery_no_warn_handler import (
    CallbackQueryNoWarnHandler,
)

from services.api.app.diabetes.handlers.registration import (
    register_handlers,
    register_profile_handlers,
    register_reminder_handlers,
)
from services.api.app.diabetes.handlers.router import callback_router
from services.api.app.diabetes.handlers import (
    security_handlers,
    reminder_handlers as rh,
    billing_handlers,
    learning_handlers,
    learning_onboarding,
)
from services.api.app.config import reload_settings


def test_register_handlers_attaches_expected_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    from services.api.app.diabetes.handlers import (
        dose_calc,
        profile as profile_handlers,
        reporting_handlers,
        photo_handlers,
        sugar_handlers,
        gpt_handlers,
    )

    app = ApplicationBuilder().token("TESTTOKEN").build()
    register_handlers(app)

    handlers = app.handlers[0]
    callbacks = [getattr(h, "callback", None) for h in handlers]

    assert gpt_handlers.freeform_handler in callbacks
    assert photo_handlers.photo_handler in callbacks
    assert photo_handlers.doc_handler in callbacks
    assert photo_handlers.prompt_photo in callbacks
    assert dose_calc.dose_cancel in callbacks
    assert sugar_handlers.prompt_sugar not in callbacks
    assert callback_router in callbacks
    assert reporting_handlers.report_period_callback in callbacks
    assert profile_handlers.profile_view in callbacks
    assert profile_handlers.profile_back in callbacks
    assert reporting_handlers.report_request in callbacks
    assert reporting_handlers.history_view in callbacks
    assert any(
        isinstance(h, CommandHandler)
        and h.callback is reporting_handlers.history_view
        and "history" in h.commands
        for h in handlers
    )
    assert gpt_handlers.chat_with_gpt in callbacks
    assert security_handlers.hypo_alert_faq in callbacks
    assert billing_handlers.trial_command in callbacks
    assert billing_handlers.upgrade_command in callbacks
    assert billing_handlers.subscription_button in callbacks
    assert any(
        isinstance(h, CommandHandler)
        and h.callback is learning_handlers.lesson_command
        and "lesson" in h.commands
        for h in handlers
    )
    assert any(
        isinstance(h, CommandHandler)
        and h.callback is learning_handlers.quiz_command
        and "quiz" in h.commands
        for h in handlers
    )
    assert any(
        isinstance(h, CommandHandler)
        and h.callback is learning_handlers.progress_command
        and "progress" in h.commands
        for h in handlers
    )
    assert any(
        isinstance(h, CommandHandler)
        and h.callback is learning_handlers.exit_command
        and "exit" in h.commands
        for h in handlers
    )
    assert any(
        isinstance(h, CommandHandler)
        and h.callback is learning_onboarding.learn_reset
        and "learn_reset" in h.commands
        for h in handlers
    )
    assert any(
        isinstance(h, MessageHandler)
        and h.callback is learning_onboarding.onboarding_reply
        for h in handlers
    )
    assert any(
        isinstance(h, MessageHandler)
        and h.callback is learning_handlers.quiz_answer_handler
        for h in handlers
    )
    # Reminder handlers should be registered
    assert any(
        isinstance(h, CallbackQueryHandler) and h.callback is rh.reminder_action_cb
        for h in handlers
    )
    assert any(
        isinstance(h, MessageHandler) and h.callback is rh.reminder_webapp_save
        for h in handlers
    )
    assert any(
        isinstance(h, CommandHandler) and h.callback is rh.add_reminder
        for h in handlers
    )

    onb_conv = [
        h
        for h in handlers
        if isinstance(h, ConversationHandler)
        and any(
            isinstance(ep, CommandHandler) and "start" in ep.commands
            for ep in h.entry_points
        )
    ]
    assert onb_conv == []

    conv_handlers = [h for h in handlers if isinstance(h, ConversationHandler)]
    assert dose_calc.dose_conv in conv_handlers
    assert sugar_handlers.sugar_conv in conv_handlers
    assert profile_handlers.profile_conv in conv_handlers
    conv_cmds = [
        ep for ep in dose_calc.dose_conv.entry_points if isinstance(ep, CommandHandler)
    ]
    assert conv_cmds and "dose" in conv_cmds[0].commands
    sugar_conv_cmds = [
        ep
        for ep in sugar_handlers.sugar_conv.entry_points
        if isinstance(ep, CommandHandler)
    ]
    assert sugar_conv_cmds and "sugar" in sugar_conv_cmds[0].commands
    profile_conv_cmd = [
        ep
        for ep in profile_handlers.profile_conv.entry_points
        if isinstance(ep, CommandHandler)
        and ep.callback is profile_handlers.profile_command
        and "profile" in ep.commands
    ]
    assert profile_conv_cmd
    profile_conv_cb = [
        ep
        for ep in profile_handlers.profile_conv.entry_points
        if isinstance(ep, CallbackQueryNoWarnHandler)
        and ep.callback is getattr(profile_handlers, "_profile_edit_entry")
    ]
    assert profile_conv_cb

    text_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is gpt_handlers.freeform_handler
    ]
    assert text_handlers

    photo_handler_msgs = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is photo_handlers.photo_handler
    ]
    assert photo_handler_msgs

    doc_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is photo_handlers.doc_handler
    ]
    assert doc_handlers

    photo_prompt_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is photo_handlers.photo_prompt
    ]
    assert photo_prompt_handlers

    sugar_cmd = [
        h
        for h in handlers
        if isinstance(h, CommandHandler) and h.callback is sugar_handlers.sugar_start
    ]
    assert not sugar_cmd

    cancel_cmd = [
        h
        for h in handlers
        if isinstance(h, CommandHandler) and h.callback is dose_calc.dose_cancel
    ]
    assert cancel_cmd and "cancel" in cancel_cmd[0].commands

    profile_view_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is profile_handlers.profile_view
    ]
    assert profile_view_handlers

    report_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler)
        and h.callback is reporting_handlers.report_request
    ]
    assert report_handlers

    report_cmd = [
        h
        for h in handlers
        if isinstance(h, CommandHandler)
        and h.callback is reporting_handlers.report_request
    ]
    assert report_cmd and "report" in report_cmd[0].commands

    gpt_cmd = [
        h
        for h in handlers
        if isinstance(h, CommandHandler) and h.callback is gpt_handlers.chat_with_gpt
    ]
    assert gpt_cmd and "gpt" in gpt_cmd[0].commands

    history_cmd = [
        h
        for h in handlers
        if isinstance(h, CommandHandler)
        and h.callback is reporting_handlers.history_view
    ]
    assert history_cmd and "history" in history_cmd[0].commands

    history_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler)
        and h.callback is reporting_handlers.history_view
    ]
    assert history_handlers

    cb_handlers = [
        h
        for h in handlers
        if isinstance(h, CallbackQueryHandler) and h.callback is callback_router
    ]
    assert cb_handlers
    report_cb_handlers = [
        h
        for h in handlers
        if isinstance(h, CallbackQueryHandler)
        and h.callback is reporting_handlers.report_period_callback
    ]
    assert report_cb_handlers
    profile_back_handlers = [
        h
        for h in handlers
        if isinstance(h, CallbackQueryHandler)
        and h.callback is profile_handlers.profile_back
    ]
    assert profile_back_handlers


def test_register_handlers_skips_learning_handlers_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LEARNING_MODE_ENABLED", "0")
    reload_settings()

    app = ApplicationBuilder().token("TESTTOKEN").build()
    register_handlers(app)

    handlers = app.handlers[0]
    commands = [
        cmd for h in handlers if isinstance(h, CommandHandler) for cmd in h.commands
    ]
    for name in ["learn", "lesson", "quiz", "progress", "exit", "learn_reset"]:
        assert name not in commands
    monkeypatch.setenv("LEARNING_MODE_ENABLED", "1")
    reload_settings()


def test_register_learning_onboarding_handlers() -> None:
    app = ApplicationBuilder().token("TESTTOKEN").build()
    learning_onboarding.register_handlers(app)

    handlers = app.handlers[0]
    assert any(
        isinstance(h, CommandHandler)
        and h.callback is learning_onboarding.learn_reset
        and "learn_reset" in h.commands
        for h in handlers
    )
    assert any(
        isinstance(h, MessageHandler)
        and h.callback is learning_onboarding.onboarding_reply
        for h in handlers
    )


def test_register_profile_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    from services.api.app.diabetes.handlers import profile as profile_handlers

    app = ApplicationBuilder().token("TESTTOKEN").build()
    register_profile_handlers(app)

    handlers = app.handlers[0]

    assert profile_handlers.profile_conv in handlers
    assert profile_handlers.profile_webapp_handler in handlers
    assert any(
        isinstance(h, MessageHandler) and h.callback is profile_handlers.profile_view
        for h in handlers
    )
    assert any(
        isinstance(h, CallbackQueryHandler)
        and h.callback is profile_handlers.profile_security
        for h in handlers
    )
    assert any(
        isinstance(h, CallbackQueryHandler)
        and h.callback is profile_handlers.profile_back
        for h in handlers
    )


def test_register_reminder_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    from services.api.app.diabetes.handlers import reminder_handlers as rh

    called = False

    def fake_schedule(job_queue: JobQueue[ContextTypes.DEFAULT_TYPE] | None) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(rh, "schedule_all", fake_schedule)

    app = ApplicationBuilder().token("TESTTOKEN").build()
    register_reminder_handlers(app)

    assert called
    handlers = app.handlers[0]

    assert any(
        isinstance(h, CommandHandler) and h.callback is rh.reminders_list
        for h in handlers
    )
    assert any(
        isinstance(h, CommandHandler) and h.callback is rh.add_reminder
        for h in handlers
    )
    assert rh.reminder_action_handler in handlers
    assert rh.reminder_webapp_handler in handlers
    assert any(
        isinstance(h, CommandHandler) and h.callback is rh.delete_reminder
        for h in handlers
    )
    assert any(
        isinstance(h, MessageHandler) and h.callback is rh.reminders_list
        for h in handlers
    )
    assert any(
        isinstance(h, CallbackQueryHandler) and h.callback is rh.reminder_callback
        for h in handlers
    )


def test_register_reminder_handlers_missing_debug_module(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    orig_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "services.api.app.diabetes.handlers.reminder_debug":
            raise ImportError("missing module")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    app = ApplicationBuilder().token("TESTTOKEN").build()

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="register_debug_reminder_handlers"):
            register_reminder_handlers(app)

    assert "Failed to load register_debug_reminder_handlers" in caplog.text


@pytest.mark.asyncio
async def test_reminders_command_renders_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = ApplicationBuilder().token("TESTTOKEN").build()
    register_reminder_handlers(app)
    handler = next(
        h
        for h in app.handlers[0]
        if isinstance(h, CommandHandler) and "reminders" in h.commands
    )

    monkeypatch.setattr(rh, "run_db", None)

    session_obj = object()

    class DummySessionCtx:
        def __enter__(self) -> object:
            return session_obj

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

    monkeypatch.setattr(rh, "SessionLocal", lambda: DummySessionCtx())

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("btn", callback_data="1")]])

    def fake_render(
        session: Session, user_id: int
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        assert session is session_obj
        assert user_id == 1
        return "rendered", keyboard

    monkeypatch.setattr(rh, "_render_reminders", fake_render)

    captured: dict[str, Any] = {}

    async def fake_reply_text(text: str, **kwargs: Any) -> None:
        captured["text"] = text
        captured["kwargs"] = kwargs

    message = MagicMock(spec=Message)
    message.reply_text = fake_reply_text

    user = MagicMock()
    user.id = 1

    update = MagicMock()
    update.effective_user = user
    update.message = message

    context = MagicMock()

    await handler.callback(update, context)

    assert captured["text"] == "rendered"
    kwargs = captured["kwargs"]
    assert kwargs.get("reply_markup") is keyboard
    assert kwargs.get("parse_mode") == "HTML"


def test_register_handlers_schedules_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    run_once_called: dict[str, Any] = {}
    run_repeating_called: dict[str, Any] = {}

    def fake_run_once(self, callback: Any, *args: Any, **kwargs: Any) -> None:
        run_once_called["callback"] = callback
        run_once_called["name"] = kwargs.get("name")

    def fake_run_repeating(self, callback: Any, *args: Any, **kwargs: Any) -> None:
        run_repeating_called["callback"] = callback
        run_repeating_called["name"] = kwargs.get("name")

    monkeypatch.setattr(JobQueue, "run_once", fake_run_once)
    monkeypatch.setattr(JobQueue, "run_repeating", fake_run_repeating)

    app = ApplicationBuilder().token("TESTTOKEN").build()
    register_handlers(app)

    assert run_once_called.get("callback") is not None
    assert run_once_called.get("name") == "clear_waiting_gpt_flags_once"
    assert run_repeating_called.get("callback") is not None
    assert run_repeating_called.get("name") == "clear_waiting_gpt_flags"
