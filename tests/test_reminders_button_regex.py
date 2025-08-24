import os

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler
from services.api.app.diabetes.utils.ui import menu_keyboard
import services.api.app.diabetes.handlers.registration as handlers
import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers
from services.api.app.diabetes.handlers import webapp_openers


def test_reminders_button_has_no_regex_handler() -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401

    button_texts = [btn.text for row in menu_keyboard.keyboard for btn in row]
    assert "⏰ Напоминания" in button_texts

    app = ApplicationBuilder().token("TESTTOKEN").build()
    handlers.register_handlers(app)

    assert not any(
        isinstance(h, MessageHandler) and h.callback is reminder_handlers.reminders_list
        for h in app.handlers[0]
    )

    assert any(
        isinstance(h, CommandHandler) and h.callback is webapp_openers.open_reminders_webapp
        for h in app.handlers[0]
    )
