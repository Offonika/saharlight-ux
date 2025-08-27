from typing import Any

from tests.telegram_stubs import CallbackContext, Update


def make_update(**kwargs: Any) -> None:
    update = Update()
    for key, value in kwargs.items():
        setattr(update, key, value)
    return update


def make_context(**kwargs: Any) -> None:
    ctx = CallbackContext()
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return ctx
