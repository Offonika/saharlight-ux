import os
import re
from typing import cast

from telegram.ext import ApplicationBuilder, MessageHandler, filters
from services.api.app.diabetes.utils.ui import menu_keyboard
import services.api.app.diabetes.handlers.registration as handlers
import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers


def test_reminders_button_matches_regex() -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401

    button_texts = [btn.text for row in menu_keyboard().keyboard for btn in row]
    assert "⏰ Напоминания" in button_texts

    app = ApplicationBuilder().token("TESTTOKEN").build()
    handlers.register_handlers(app)
    reminder_handler = next(
        h
        for h in app.handlers[0]
        if isinstance(h, MessageHandler)
        and h.callback is reminder_handlers.reminders_list
    )
    pattern = cast(filters.Regex, reminder_handler.filters).pattern.pattern
    assert pattern == "^⏰ Напоминания$"
    assert re.fullmatch(pattern, "⏰ Напоминания")
