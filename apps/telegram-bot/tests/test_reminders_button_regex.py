import os
import re
from telegram.ext import ApplicationBuilder, MessageHandler
from diabetes.ui import menu_keyboard
import diabetes.common_handlers as handlers
import diabetes.reminder_handlers as reminder_handlers


def test_reminders_button_matches_regex():
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import diabetes.openai_utils as openai_utils  # noqa: F401

    button_texts = [btn.text for row in menu_keyboard.keyboard for btn in row]
    assert "⏰ Напоминания" in button_texts

    app = ApplicationBuilder().token("TESTTOKEN").build()
    handlers.register_handlers(app)
    reminder_handler = next(
        h
        for h in app.handlers[0]
        if isinstance(h, MessageHandler) and h.callback is reminder_handlers.reminders_list
    )
    pattern = reminder_handler.filters.pattern.pattern
    assert pattern == "^⏰ Напоминания$"
    assert re.fullmatch(pattern, "⏰ Напоминания")

