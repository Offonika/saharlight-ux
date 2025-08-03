import os

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
)

from diabetes.common_handlers import register_handlers, callback_router, start_command


def test_register_handlers_attaches_expected_handlers(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import diabetes.openai_utils as openai_utils  # noqa: F401
    from diabetes import dose_handlers, profile_handlers, reporting_handlers

    app = ApplicationBuilder().token("TESTTOKEN").build()
    register_handlers(app)

    handlers = app.handlers[0]
    callbacks = [h.callback for h in handlers]

    assert start_command in callbacks
    assert profile_handlers.profile_command in callbacks
    assert dose_handlers.freeform_handler in callbacks
    assert dose_handlers.photo_handler in callbacks
    assert dose_handlers.doc_handler in callbacks
    assert dose_handlers.prompt_photo in callbacks
    assert dose_handlers.prompt_sugar in callbacks
    assert dose_handlers.prompt_dose in callbacks
    assert callback_router in callbacks
    assert profile_handlers.profile_view in callbacks
    assert reporting_handlers.report_request in callbacks
    assert reporting_handlers.history_view in callbacks

    start_cmd = [
        h for h in handlers if isinstance(h, CommandHandler) and h.callback is start_command
    ]
    assert start_cmd and "start" in start_cmd[0].commands

    profile_cmd = [
        h
        for h in handlers
        if isinstance(h, CommandHandler) and h.callback is profile_handlers.profile_command
    ]
    assert profile_cmd and "profile" in profile_cmd[0].commands

    dose_cmd = [
        h for h in handlers if isinstance(h, CommandHandler) and h.callback is dose_handlers.freeform_handler
    ]
    assert dose_cmd and "dose" in dose_cmd[0].commands

    text_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is dose_handlers.freeform_handler
    ]
    assert text_handlers

    photo_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is dose_handlers.photo_handler
    ]
    assert photo_handlers

    doc_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is dose_handlers.doc_handler
    ]
    assert doc_handlers

    prompt_photo_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is dose_handlers.prompt_photo
    ]
    assert prompt_photo_handlers

    prompt_sugar_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is dose_handlers.prompt_sugar
    ]
    assert prompt_sugar_handlers

    prompt_dose_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is dose_handlers.prompt_dose
    ]
    assert prompt_dose_handlers

    profile_view_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is profile_handlers.profile_view
    ]
    assert profile_view_handlers

    report_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is reporting_handlers.report_request
    ]
    assert report_handlers

    report_cmd = [
        h
        for h in handlers
        if isinstance(h, CommandHandler) and h.callback is reporting_handlers.report_request
    ]
    assert report_cmd and "report" in report_cmd[0].commands

    history_handlers = [
        h
        for h in handlers
        if isinstance(h, MessageHandler) and h.callback is reporting_handlers.history_view
    ]
    assert history_handlers

    cb_handlers = [
        h
        for h in handlers
        if isinstance(h, CallbackQueryHandler) and h.callback is callback_router
    ]
    assert cb_handlers
