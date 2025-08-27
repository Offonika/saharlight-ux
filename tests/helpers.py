from typing import Any

from tests.telegram_stubs import CallbackContext, Update


def make_update(**kwargs: Any) -> Update:
    update = Update()
    for key, value in kwargs.items():
        setattr(update, key, value)
    return update


def make_context(**kwargs: Any) -> CallbackContext:
    ctx = CallbackContext()
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return ctx
