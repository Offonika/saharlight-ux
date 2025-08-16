import re
from typing import Any, Awaitable, Callable, Optional

from telegram import CallbackQuery, Update
from telegram.ext import BaseHandler, CallbackContext

CallbackQueryHandlerCallback = Callable[[Update, CallbackContext], Awaitable[Any]]


class CallbackQueryNoWarnHandler(BaseHandler[Update, CallbackContext]):
    """Handle callback queries without triggering ConversationHandler warnings."""

    def __init__(
        self,
        callback: CallbackQueryHandlerCallback,
        pattern: str | None = None,
    ) -> None:
        super().__init__(callback)
        self.pattern: Optional[re.Pattern[str]] = re.compile(pattern) if pattern else None

    def check_update(self, update: object) -> Optional[CallbackQuery]:
        if isinstance(update, Update) and update.callback_query:
            data = update.callback_query.data or ""
            if self.pattern is None or self.pattern.match(data):
                return update.callback_query
        return None
