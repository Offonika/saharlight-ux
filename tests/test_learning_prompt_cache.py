import types
from collections import OrderedDict
from types import SimpleNamespace

import pytest

from services.api.app import config
from services.api.app.diabetes.llm_router import LLMTask
from services.api.app.diabetes.services import gpt_client


@pytest.mark.asyncio
async def test_learning_cache_reuses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    async def fake_create_chat_completion(*, model: str, **kwargs: object) -> object:
        nonlocal call_count
        call_count += 1
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))])

    monkeypatch.setattr(gpt_client, "create_chat_completion", fake_create_chat_completion)
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            learning_prompt_cache=True,
            learning_prompt_cache_size=128,
            learning_prompt_cache_ttl_sec=1000,
        ),
    )
    monkeypatch.setattr(
        gpt_client,
        "_learning_router",
        gpt_client.LLMRouter("gpt-4o-mini"),
        raising=False,
    )
    monkeypatch.setattr(gpt_client, "_learning_cache", OrderedDict())

    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]

    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=messages)
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=messages)

    assert call_count == 1


@pytest.mark.asyncio
async def test_learning_cache_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    async def fake_create_chat_completion(*, model: str, **kwargs: object) -> object:
        nonlocal call_count
        call_count += 1
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))])

    monkeypatch.setattr(gpt_client, "create_chat_completion", fake_create_chat_completion)
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            learning_prompt_cache=False,
            learning_prompt_cache_size=128,
            learning_prompt_cache_ttl_sec=1000,
        ),
    )
    monkeypatch.setattr(
        gpt_client,
        "_learning_router",
        gpt_client.LLMRouter("gpt-4o-mini"),
        raising=False,
    )
    monkeypatch.setattr(gpt_client, "_learning_cache", OrderedDict())

    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]

    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=messages)
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=messages)

    assert call_count == 2


@pytest.mark.asyncio
async def test_learning_cache_key_components(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    async def fake_create_chat_completion(*, model: str, **kwargs: object) -> object:
        nonlocal call_count
        call_count += 1
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))])

    monkeypatch.setattr(gpt_client, "create_chat_completion", fake_create_chat_completion)
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            learning_prompt_cache=True,
            learning_prompt_cache_size=128,
            learning_prompt_cache_ttl_sec=1000,
        ),
    )
    monkeypatch.setattr(
        gpt_client,
        "_learning_router",
        gpt_client.LLMRouter("m1"),
        raising=False,
    )
    monkeypatch.setattr(gpt_client, "_learning_cache", OrderedDict())

    msg_base = [
        {"role": "system", "content": "sys1"},
        {"role": "user", "content": "u1"},
    ]

    # initial call populates cache
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=msg_base)
    # same prompts => hit
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=msg_base)
    assert call_count == 1

    # different system prompt => miss
    msg_system = [
        {"role": "system", "content": "sys2"},
        {"role": "user", "content": "u1"},
    ]
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=msg_system)
    assert call_count == 2

    # different user prompt => miss
    msg_user = [
        {"role": "system", "content": "sys1"},
        {"role": "user", "content": "u2"},
    ]
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=msg_user)
    assert call_count == 3

    # different model => miss
    monkeypatch.setattr(
        gpt_client,
        "_learning_router",
        gpt_client.LLMRouter("m2"),
        raising=False,
    )
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=msg_base)

    assert call_count == 4


@pytest.mark.asyncio
async def test_learning_cache_respects_size(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    async def fake_create_chat_completion(*, model: str, **kwargs: object) -> object:
        nonlocal call_count
        call_count += 1
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))])

    monkeypatch.setattr(gpt_client, "create_chat_completion", fake_create_chat_completion)
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            learning_prompt_cache=True,
            learning_prompt_cache_size=2,
            learning_prompt_cache_ttl_sec=1000,
        ),
    )
    monkeypatch.setattr(
        gpt_client,
        "_learning_router",
        gpt_client.LLMRouter("m1"),
        raising=False,
    )
    monkeypatch.setattr(gpt_client, "_learning_cache", OrderedDict())

    def make_msgs(i: int) -> list[dict[str, str]]:
        return [{"role": "system", "content": "s"}, {"role": "user", "content": f"u{i}"}]

    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=make_msgs(1))
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=make_msgs(2))
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=make_msgs(1))
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=make_msgs(3))
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=make_msgs(2))

    assert call_count == 4
    assert len(gpt_client._learning_cache) == 2


@pytest.mark.asyncio
async def test_learning_cache_respects_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    async def fake_create_chat_completion(*, model: str, **kwargs: object) -> object:
        nonlocal call_count
        call_count += 1
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))])

    monkeypatch.setattr(gpt_client, "create_chat_completion", fake_create_chat_completion)
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            learning_prompt_cache=True,
            learning_prompt_cache_size=128,
            learning_prompt_cache_ttl_sec=1,
        ),
    )
    monkeypatch.setattr(
        gpt_client,
        "_learning_router",
        gpt_client.LLMRouter("m1"),
        raising=False,
    )
    monkeypatch.setattr(gpt_client, "_learning_cache", OrderedDict())

    start = 100.0
    monkeypatch.setattr(gpt_client.time, "time", lambda: start)

    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]

    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=messages)
    monkeypatch.setattr(gpt_client.time, "time", lambda: start + 0.5)
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=messages)
    assert call_count == 1
    monkeypatch.setattr(gpt_client.time, "time", lambda: start + 2)
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=messages)
    assert call_count == 2
