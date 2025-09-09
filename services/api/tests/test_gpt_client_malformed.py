from __future__ import annotations

import pytest

from services.api.app import config
from services.api.app.diabetes.llm_router import LLMTask
from services.api.app.diabetes.services import gpt_client


class DummyMessage:
    def __init__(self, content: str | None) -> None:
        self.content = content


class DummyChoice:
    def __init__(self, content: str | None) -> None:
        self.message = DummyMessage(content)


class DummyCompletion:
    def __init__(self, choices: list[DummyChoice]) -> None:
        self.choices = choices


@pytest.mark.asyncio()
async def test_create_learning_chat_completion_no_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_completion(**_: object) -> DummyCompletion:
        return DummyCompletion([])

    monkeypatch.setattr(gpt_client, "create_chat_completion", fake_completion)
    settings = config.get_settings()
    monkeypatch.setattr(settings, "learning_prompt_cache", False, raising=False)
    with pytest.raises(ValueError, match="no choices"):
        await gpt_client.create_learning_chat_completion(
            task=LLMTask.EXPLAIN_STEP,
            messages=[{"role": "user", "content": "hi"}],
        )


@pytest.mark.asyncio()
async def test_create_learning_chat_completion_empty_content(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_completion(**_: object) -> DummyCompletion:
        return DummyCompletion([DummyChoice("")])

    monkeypatch.setattr(gpt_client, "create_chat_completion", fake_completion)
    settings = config.get_settings()
    monkeypatch.setattr(settings, "learning_prompt_cache", False, raising=False)
    with pytest.raises(ValueError, match="empty content"):
        await gpt_client.create_learning_chat_completion(
            task=LLMTask.EXPLAIN_STEP,
            messages=[{"role": "user", "content": "hi"}],
        )
