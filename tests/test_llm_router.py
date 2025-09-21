from __future__ import annotations

import pytest

import types

from services.api.app import config
from services.api.app.diabetes.llm_router import LLMRouter, LLMTask
from services.api.app.diabetes.services import gpt_client


def test_router_returns_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """All tasks should map to the default model unless overridden."""
    settings = config.get_settings()
    monkeypatch.setattr(settings, "learning_model_default", "gpt-4o-mini")
    router = LLMRouter()
    for task in (
        LLMTask.EXPLAIN_STEP,
        LLMTask.QUIZ_CHECK,
        LLMTask.LONG_PLAN,
    ):
        assert router.choose_model(task) == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_create_learning_chat_completion_uses_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """gpt_client should delegate model selection to the router."""
    captured: dict[str, str] = {}

    async def fake_create_chat_completion(*, model: str, **kwargs: object) -> object:
        captured["model"] = model
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))]
        )

    monkeypatch.setattr(
        gpt_client, "create_chat_completion", fake_create_chat_completion
    )
    settings = config.get_settings()
    monkeypatch.setattr(settings, "learning_model_default", "gpt-4o-mini")
    router = LLMRouter()
    observed: list[LLMTask] = []

    def fake_choose_model(task: LLMTask) -> str:
        observed.append(task)
        return router.choose_model(task)

    monkeypatch.setattr(gpt_client, "choose_model", fake_choose_model)

    await gpt_client.create_learning_chat_completion(
        task=LLMTask.EXPLAIN_STEP,
        messages=[],
    )

    assert captured["model"] == "gpt-4o-mini"
    assert observed == [LLMTask.EXPLAIN_STEP]
