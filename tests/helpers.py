from types import SimpleNamespace
from typing import Any, cast

from telegram import Update
from telegram.ext import CallbackContext


def make_update(**kwargs: Any) -> Update:
    return cast(Update, SimpleNamespace(**kwargs))


def make_context(**kwargs: Any) -> CallbackContext[Any, Any, Any, Any]:
    return cast(CallbackContext[Any, Any, Any, Any], SimpleNamespace(**kwargs))
