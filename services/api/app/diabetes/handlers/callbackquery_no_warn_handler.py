import re
from typing import Callable, Coroutine, Optional, TYPE_CHECKING

from telegram import CallbackQuery, Update
from telegram.ext import BaseHandler, ContextTypes

if TYPE_CHECKING:
    BaseCBHandler = BaseHandler[CallbackQuery, ContextTypes.DEFAULT_TYPE]  # type: ignore[type-arg]
else:  # pragma: no cover - runtime uses unsubscripted class
    BaseCBHandler = BaseHandler

CallbackQueryHandlerCallback = Callable[
    [Update, ContextTypes.DEFAULT_TYPE], Coroutine[object, object, int | None]
]


class CallbackQueryNoWarnHandler(BaseCBHandler):
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

    def check_update(self, update: object) -> Optional[CallbackQuery]:
        if isinstance(update, Update) and update.callback_query:
            data = update.callback_query.data or ""
            if self.pattern is None or self.pattern.match(data):
                return update.callback_query
        return None
