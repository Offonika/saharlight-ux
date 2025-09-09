from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
import logging
import pytest
from telegram import Chat, Message, Update, User

from services.api.app.diabetes import learning_handlers


@pytest.mark.asyncio
async def test_hydrate_backfills_profile(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    user = User(id=1, is_bot=False, first_name="T")
    chat = Chat(id=1, type="private")
    msg = Message(
        message_id=1,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text="hi",
    )
    update = Update(update_id=1, message=msg)
    context = SimpleNamespace(
        user_data={"learn_profile_overrides": {"age_group": "adult", "learning_level": "novice"}},
        bot_data={},
    )

    async def fake_get(uid: int) -> None:
        return None

    calls: list[tuple[int, str | None, str | None, str | None]] = []

    async def fake_upsert(
        uid: int,
        *,
        age_group: str | None = None,
        learning_level: str | None = None,
        diabetes_type: str | None = None,
    ) -> None:
        calls.append((uid, age_group, learning_level, diabetes_type))

    monkeypatch.setattr(learning_handlers, "get_learning_profile", fake_get)
    monkeypatch.setattr(learning_handlers, "upsert_learning_profile", fake_upsert)

    with caplog.at_level(logging.INFO):
        ok = await learning_handlers._hydrate(update, context)
    assert ok is True
    assert calls == [(1, "adult", "novice", None)]
    assert "learning_profile backfilled user_id=1" in caplog.text
    assert context.user_data["learning_profile_backfilled"] is True

    with caplog.at_level(logging.INFO):
        ok2 = await learning_handlers._hydrate(update, context)
    assert ok2 is True
    assert calls == [(1, "adult", "novice", None)]
