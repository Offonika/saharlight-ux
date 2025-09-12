from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.orm import Session, sessionmaker
from telegram import Update
from telegram.ext import ContextTypes

from services.api.app.diabetes.handlers import router
from services.api.app.diabetes.services.db import Profile


class DummyQuery:
    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.edited: list[str] = []

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edited.append(text)


@pytest.mark.asyncio
async def test_profile_timezone_update_success(
    session_local: sessionmaker[Session],
) -> None:
    query = DummyQuery("profile_timezone:Europe/Moscow", 1)
    update = cast(Update, SimpleNamespace(callback_query=query, effective_user=query.from_user))
    context = cast(ContextTypes.DEFAULT_TYPE, SimpleNamespace())

    await router.handle_profile_timezone(update, context, query, query.data)

    assert query.edited == ["✅ Часовой пояс обновлён."]
    with session_local() as session:
        profile = session.get(Profile, 1)
        assert profile is not None
        assert profile.timezone == "Europe/Moscow"
        assert profile.timezone_auto is False


@pytest.mark.asyncio
async def test_profile_timezone_invalid(session_local: sessionmaker[Session]) -> None:
    query = DummyQuery("profile_timezone:Invalid/Zone", 1)
    update = cast(Update, SimpleNamespace(callback_query=query, effective_user=query.from_user))
    context = cast(ContextTypes.DEFAULT_TYPE, SimpleNamespace())

    await router.handle_profile_timezone(update, context, query, query.data)

    assert query.edited == ["Некорректный часовой пояс."]
    with session_local() as session:
        profile = session.get(Profile, 1)
        assert profile is None
