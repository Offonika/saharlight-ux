from __future__ import annotations

import pytest

from services.api.app.diabetes import dynamic_tutor


@pytest.mark.asyncio
async def test_affirmative_skips_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_call(**_: object) -> str:
        raise AssertionError("LLM should not be called")

    monkeypatch.setattr(dynamic_tutor, "create_learning_chat_completion", fail_call)

    correct, feedback = await dynamic_tutor.check_user_answer({}, "t", "да", "step")

    assert correct is True
    assert feedback.startswith("✅")
