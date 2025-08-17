import pytest
from typing import Callable
from telegram import CallbackQuery, Update, User
from telegram.ext import ContextTypes

from services.api.app.diabetes.handlers.callbackquery_no_warn_handler import (
    CallbackQueryNoWarnHandler,
)


@pytest.fixture()
def handler() -> CallbackQueryNoWarnHandler:
    async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
        return None

    return CallbackQueryNoWarnHandler(callback, pattern="^match$")


@pytest.fixture()
def user() -> User:
    return User(id=1, first_name="Test", is_bot=False)


@pytest.fixture()
def make_update(user: User) -> Callable[[str | None], Update]:
    def _make_update(data: str | None) -> Update:
        if data is None:
            return Update(update_id=1)
        callback_query = CallbackQuery(
            id="1",
            from_user=user,
            chat_instance="1",
            data=data,
        )
        return Update(update_id=1, callback_query=callback_query)

    return _make_update


def test_check_update_no_callback_query(
    handler: CallbackQueryNoWarnHandler, make_update: Callable[[str | None], Update]
) -> None:
    update = make_update(None)
    assert handler.check_update(update) is None


def test_check_update_non_matching_pattern(
    handler: CallbackQueryNoWarnHandler, make_update: Callable[[str | None], Update]
) -> None:
    update = make_update("other")
    assert handler.check_update(update) is None


def test_check_update_matching_pattern(
    handler: CallbackQueryNoWarnHandler, make_update: Callable[[str | None], Update]
) -> None:
    update = make_update("match")
    assert handler.check_update(update) is update.callback_query
