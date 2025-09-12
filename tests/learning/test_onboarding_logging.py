from __future__ import annotations

import logging
from typing import Mapping

import pytest

from services.api.app.diabetes import learning_handlers, learning_onboarding as onboarding_utils
from tests.utils.telegram import make_context, make_update


class DummyMessage:
    async def reply_text(self, text: str, **_: object) -> None:  # pragma: no cover - helper
        return None


@pytest.mark.asyncio
async def test_onboarding_logs(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    async def fake_profile(_: int, __: object) -> Mapping[str, object]:
        return {}

    monkeypatch.setattr(onboarding_utils.profiles, "get_profile_for_user", fake_profile)

    update = make_update(message=DummyMessage())
    context = make_context()

    with caplog.at_level(logging.INFO):
        await onboarding_utils.ensure_overrides(update, context)

    record = next(r for r in caplog.records if r.message == "ensure_overrides")
    for field in ("user_id", "has_age", "has_level", "has_dtype", "branch", "reason"):
        assert hasattr(record, field)

    caplog.clear()

    async def fake_get_learning_profile(_: int) -> None:
        return None

    async def fake_upsert(
        uid: int,
        *,
        age_group: str | None = None,
        learning_level: str | None = None,
        diabetes_type: str | None = None,
    ) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "get_learning_profile", fake_get_learning_profile)
    monkeypatch.setattr(learning_handlers, "upsert_learning_profile", fake_upsert)

    update2 = make_update()
    context2 = make_context(
        user_data={
            "learn_profile_overrides": {"age_group": "adult", "learning_level": "novice"},
            "learning_plan": [],
            "learning_plan_index": 0,
        }
    )

    with caplog.at_level(logging.INFO):
        await learning_handlers._hydrate(update2, context2)

    record2 = next(r for r in caplog.records if r.message.startswith("learning_profile backfilled"))
    for field in ("user_id", "has_age", "has_level", "has_dtype", "branch", "reason"):
        assert hasattr(record2, field)
