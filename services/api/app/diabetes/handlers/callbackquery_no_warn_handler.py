import re
from typing import Any, Callable, Coroutine, Optional

from telegram import CallbackQuery, Update
from telegram.ext import ContextTypes
from telegram.ext._basehandler import BaseHandler

CallbackQueryHandlerCallback = Callable[
    [Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, int | None]
]


class CallbackQueryNoWarnHandler(BaseHandler[Update, ContextTypes.DEFAULT_TYPE]):
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
