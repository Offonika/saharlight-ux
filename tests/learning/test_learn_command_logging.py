from __future__ import annotations

import logging
from typing import Mapping, cast

import pytest

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from tests.utils.telegram import make_context, make_update


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(
        self, text: str, **_: object
    ) -> None:  # pragma: no cover - helper
        self.replies.append(text)


@pytest.mark.asyncio
async def test_learn_command_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_ui_show_topics", False)

    async def fake_get_profile(user_id: int, ctx: object) -> Mapping[str, object]:
        return {}

    monkeypatch.setattr(
        learning_handlers.profiles, "get_profile_for_user", fake_get_profile
    )

    async def fake_hydrate(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "_hydrate", fake_hydrate)

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        user_data = cast(dict[str, object], context.user_data)
        user_data["learn_onboarding_stage"] = "age_group"
        return False

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context()

    with caplog.at_level(logging.INFO):
        await learning_handlers.learn_command(update, context)

    assert any(
        r.message == "learn_command" and r.asked == "age" for r in caplog.records
    )
