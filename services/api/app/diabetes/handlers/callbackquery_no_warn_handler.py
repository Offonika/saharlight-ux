import re
from typing import Callable, Coroutine, Optional, cast

from telegram import Update
from telegram.ext import BaseHandler, ContextTypes

CallbackQueryHandlerCallback = Callable[
    [Update, ContextTypes.DEFAULT_TYPE], Coroutine[object, object, object]
]


class CallbackQueryNoWarnHandler(
    BaseHandler[Update, ContextTypes.DEFAULT_TYPE, object]
):
    """Handle callback queries without triggering ConversationHandler warnings."""

    def __init__(
        self,
        callback: CallbackQueryHandlerCallback,
        pattern: str | None = None,
    ) -> None:
        BaseHandler.__init__(self, callback)
        self.callback = callback
        self.pattern: Optional[re.Pattern[str]] = (
            re.compile(pattern) if pattern else None
        )

    def check_update(self, update: object) -> Optional[Update]:
        if isinstance(update, Update) and update.callback_query:
            data = update.callback_query.data or ""
            if self.pattern is None or self.pattern.match(data):
                return cast(Update, update.callback_query)
        return None
