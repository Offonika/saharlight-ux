import re
from typing import Optional

from telegram import CallbackQuery, Update
from telegram.ext import BaseHandler


class CallbackQueryNoWarnHandler(BaseHandler):
    """Handle callback queries without triggering ConversationHandler warnings."""

    def __init__(self, callback, pattern: str | None = None):
        super().__init__(callback)
        self.pattern: Optional[re.Pattern[str]] = re.compile(pattern) if pattern else None

    def check_update(self, update: object) -> Optional[CallbackQuery]:
        if isinstance(update, Update) and update.callback_query:
            data = update.callback_query.data or ""
            if self.pattern is None or self.pattern.match(data):
                return update.callback_query
        return None
