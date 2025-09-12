from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError

from services.api.app.diabetes import learning_handlers


@pytest.mark.asyncio
async def test_persist_removes_plan_id_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_data: dict[str, Any] = {
        "learning_plan": ["step1"],
        "learning_plan_id": 1,
    }
    bot_data: dict[str, object] = {}

    async def fail_update_plan(plan_id: int, plan_json: list[str]) -> None:
        raise SQLAlchemyError("fail")

    monkeypatch.setattr(learning_handlers.plans_repo, "update_plan", fail_update_plan)

    await learning_handlers._persist(1, user_data, bot_data)

    assert "learning_plan_id" not in user_data
