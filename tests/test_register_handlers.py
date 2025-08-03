import os

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler

from diabetes.common_handlers import register_handlers, callback_router


def test_register_handlers_attaches_expected_handlers(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import diabetes.openai_utils as openai_utils  # noqa: F401
    from diabetes import dose_handlers, profile_handlers

    app = ApplicationBuilder().token("TESTTOKEN").build()
    register_handlers(app)

    handlers = app.handlers[0]
    callbacks = [h.callback for h in handlers]

    assert profile_handlers.profile_command in callbacks
    assert dose_handlers.freeform_handler in callbacks
    assert dose_handlers.photo_handler in callbacks
    assert dose_handlers.doc_handler in callbacks
    assert callback_router in callbacks

    profile_cmd = [
        h for h in handlers if isinstance(h, CommandHandler) and h.callback is profile_handlers.profile_command
    ]
    assert profile_cmd and "profile" in profile_cmd[0].commands

    dose_cmd = [
        h for h in handlers if isinstance(h, CommandHandler) and h.callback is dose_handlers.freeform_handler
    ]
    assert dose_cmd and "dose" in dose_cmd[0].commands

    text_handlers = [
        h for h in handlers
        if isinstance(h, MessageHandler) and h.callback is dose_handlers.freeform_handler
    ]
    assert text_handlers

    photo_handlers = [
        h for h in handlers
        if isinstance(h, MessageHandler) and h.callback is dose_handlers.photo_handler
    ]
    assert photo_handlers

    doc_handlers = [
        h for h in handlers
        if isinstance(h, MessageHandler) and h.callback is dose_handlers.doc_handler
    ]
    assert doc_handlers

    cb_handlers = [
        h for h in handlers
        if isinstance(h, CallbackQueryHandler) and h.callback is callback_router
    ]
    assert cb_handlers
