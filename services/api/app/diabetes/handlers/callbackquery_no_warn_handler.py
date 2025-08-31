import re
from typing import Callable, Coroutine, Optional, TYPE_CHECKING, Protocol, TypeVar, Generic

from telegram import CallbackQuery, Update
from telegram.ext import ContextTypes

CallbackQueryHandlerCallback = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[object, object, int | None]]

if TYPE_CHECKING:
    U = TypeVar("U")
    C = TypeVar("C")

    class BaseHandler(Protocol, Generic[U, C]):
        def __init__(self, callback: CallbackQueryHandlerCallback, /, **kwargs: object) -> None: ...

        def check_update(self, update: object, /) -> Optional[U]: ...
else:
    from telegram.ext._basehandler import BaseHandler


class CallbackQueryNoWarnHandler(BaseHandler[CallbackQuery, ContextTypes.DEFAULT_TYPE]):
    """Handle callback queries without triggering ConversationHandler warnings."""

    def __init__(
        self,
        callback: CallbackQueryHandlerCallback,
        pattern: str | None = None,
    ) -> None:
        super().__init__(callback)
        self.callback = callback
        self.pattern: Optional[re.Pattern[str]] = re.compile(pattern) if pattern else None

    def check_update(self, update: object) -> Optional[CallbackQuery]:
        if isinstance(update, Update) and update.callback_query:
            data = update.callback_query.data or ""
            if self.pattern is None or self.pattern.match(data):
                return update.callback_query
        return None
