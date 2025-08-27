import os

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)
from services.api.app.diabetes.handlers.callbackquery_no_warn_handler import (
    CallbackQueryNoWarnHandler,
)
from services.api.app.diabetes.handlers.registration import register_handlers
from services.api.app.diabetes.handlers.router import callback_router
from services.api.app.diabetes.handlers.onboarding_handlers import start_command
from services.api.app.diabetes.handlers.security_handlers import hypo_alert_faq
from services.api.app.diabetes.handlers.reminder_handlers import (
    reminder_action_cb,
    reminder_webapp_save,
    add_reminder,
)
from services.api.app.diabetes.handlers.dose_handlers import (
    freeform_handler,
    photo_handler,
    doc_handler,
    photo_prompt,
    dose_cancel,
    chat_with_gpt,
    dose_conv,
    sugar_conv,
    sugar_start,
    prompt_sugar,
)
from services.api.app.diabetes.handlers.profile import (
    profile_view,
    profile_back,
    profile_conv,
    profile_command,
    profile_edit,
)
from services.api.app.diabetes.handlers.reporting_handlers import (
    report_request,
    history_view,
    report_period_callback,
)


def test_register_handlers_attaches_expected_handlers(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401

    app = ApplicationBuilder().token("TESTTOKEN").build()
    register_handlers(app)

    handlers = app.handlers[0]
    callbacks = [getattr(h, "callback", None) for h in handlers]

    assert freeform_handler in callbacks
    assert photo_handler in callbacks
    assert doc_handler in callbacks
    assert photo_prompt in callbacks
    assert dose_cancel in callbacks
    assert prompt_sugar not in callbacks
    assert callback_router in callbacks
    assert report_period_callback in callbacks
    assert profile_view in callbacks
    assert profile_back in callbacks
    assert report_request in callbacks
    assert history_view in callbacks
    assert chat_with_gpt in callbacks
    assert hypo_alert_faq in callbacks
    # Reminder handlers should be registered
    assert any(
        isinstance(h, CallbackQueryHandler) and h.callback is reminder_action_cb
        for h in handlers
    )
    assert any(
        isinstance(h, MessageHandler) and h.callback is reminder_webapp_save
        for h in handlers
    )
    assert any(
        isinstance(h, CommandHandler) and h.callback is add_reminder
        for h in handlers
    )

    onb_conv = [
        h
        for h in handlers
        if isinstance(h, ConversationHandler)
        and any(
            isinstance(ep, CommandHandler)
            and ep.callback is start_command
            and "start" in ep.commands
            for ep in h.entry_points
        )
    ]
    assert onb_conv


    conv_handlers = [h for h in handlers if isinstance(h, ConversationHandler)]
    assert dose_conv in conv_handlers
    assert sugar_conv in conv_handlers
    assert profile_conv in conv_handlers
    assert onb_conv[0] in conv_handlers
    conv_cmds = [
        ep
        for ep in dose_conv.entry_points
        if isinstance(ep, CommandHandler)
    ]
    assert conv_cmds and "dose" in conv_cmds[0].commands
    sugar_conv_cmds = [
        ep
        for ep in sugar_conv.entry_points
        if isinstance(ep, CommandHandler)
    ]
    assert sugar_conv_cmds and "sugar" in sugar_conv_cmds[0].commands
    profile_conv_cmd = [
        ep
        for ep in profile_conv.entry_points
        if isinstance(ep, CommandHandler)
        and ep.callback is profile_command
        and "profile" in ep.commands
    ]
    assert profile_conv_cmd
    profile_conv_cb = [
        ep
        for ep in profile_conv.entry_points
        if isinstance(ep, CallbackQueryNoWarnHandler) and ep.callback is profile_edit
    ]
    assert profile_conv_cb

    text_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is freeform_handler
    ]
    assert text_handlers

    photo_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is photo_handler
    ]
    assert photo_handlers

    doc_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is doc_handler
    ]
    assert doc_handlers


    photo_prompt_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is photo_prompt
    ]
    assert photo_prompt_handlers

    sugar_cmd = [
        h
        for h in handlers
        if isinstance(h, CommandHandler) and h.callback is sugar_start
    ]
    assert not sugar_cmd

    cancel_cmd = [
        h
        for h in handlers
        if isinstance(h, CommandHandler) and h.callback is dose_cancel
    ]
    assert cancel_cmd and "cancel" in cancel_cmd[0].commands

    profile_view_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is profile_view
    ]
    assert profile_view_handlers

    report_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is report_request
    ]
    assert report_handlers

    report_cmd = [
        h
        for h in handlers
        if isinstance(h, CommandHandler) and h.callback is report_request
    ]
    assert report_cmd and "report" in report_cmd[0].commands

    gpt_cmd = [
        h
        for h in handlers
        if isinstance(h, CommandHandler) and h.callback is chat_with_gpt
    ]
    assert gpt_cmd and "gpt" in gpt_cmd[0].commands

    history_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is history_view
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
        and h.callback is report_period_callback
    ]
    assert report_cb_handlers
    profile_back_handlers = [
        h
        for h in handlers
        if isinstance(h, CallbackQueryHandler) and h.callback is profile_back
    ]
    assert profile_back_handlers
