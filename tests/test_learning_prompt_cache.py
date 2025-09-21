import types
from collections import OrderedDict
from types import SimpleNamespace

import pytest

from services.api.app import config
from services.api.app.diabetes.llm_router import LLMTask
from services.api.app.diabetes.metrics import (
    get_metric_value,
    learning_prompt_cache_hit,
    learning_prompt_cache_miss,
)
from services.api.app.diabetes.services import gpt_client


def setup_function() -> None:
    """Reset cache metrics before each test."""
    learning_prompt_cache_hit._value.set(0)  # type: ignore[attr-defined] # noqa: SLF001
    learning_prompt_cache_miss._value.set(0)  # type: ignore[attr-defined] # noqa: SLF001


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
    monkeypatch.setattr(gpt_client, "choose_model", lambda task: "gpt-4o-mini")
    monkeypatch.setattr(gpt_client, "_learning_cache", OrderedDict())

    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]

    base_hit = get_metric_value(learning_prompt_cache_hit)
    base_miss = get_metric_value(learning_prompt_cache_miss)

    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=messages)
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=messages)

    assert call_count == 1
    assert get_metric_value(learning_prompt_cache_miss) == base_miss + 1
    assert get_metric_value(learning_prompt_cache_hit) == base_hit + 1


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
    monkeypatch.setattr(gpt_client, "choose_model", lambda task: "gpt-4o-mini")
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
    model_name = {"value": "m1"}

    def choose(task: LLMTask) -> str:
        return model_name["value"]

    monkeypatch.setattr(gpt_client, "choose_model", choose)
    monkeypatch.setattr(gpt_client, "_learning_cache", OrderedDict())

    msg_base = [
        {
            "role": "system",
            "content": "sys1",
            "user_id": "u1",
            "plan_id": "p1",
            "topic_slug": "t1",
            "step_idx": 1,
        },
        {"role": "user", "content": "u1"},
    ]

    # initial call populates cache
    await gpt_client.create_learning_chat_completion(
        task=LLMTask.EXPLAIN_STEP, messages=msg_base
    )
    # same prompts => hit
    await gpt_client.create_learning_chat_completion(
        task=LLMTask.EXPLAIN_STEP, messages=msg_base
    )
    assert call_count == 1

    # different system prompt => miss
    msg_system = [
        {
            "role": "system",
            "content": "sys2",
            "user_id": "u1",
            "plan_id": "p1",
            "topic_slug": "t1",
            "step_idx": 1,
        },
        {"role": "user", "content": "u1"},
    ]
    await gpt_client.create_learning_chat_completion(
        task=LLMTask.EXPLAIN_STEP, messages=msg_system
    )
    assert call_count == 2

    # different user prompt => miss
    msg_user = [
        {
            "role": "system",
            "content": "sys1",
            "user_id": "u1",
            "plan_id": "p1",
            "topic_slug": "t1",
            "step_idx": 1,
        },
        {"role": "user", "content": "u2"},
    ]
    await gpt_client.create_learning_chat_completion(
        task=LLMTask.EXPLAIN_STEP, messages=msg_user
    )
    assert call_count == 3

    # different model => miss
    model_name["value"] = "m2"
    await gpt_client.create_learning_chat_completion(
        task=LLMTask.EXPLAIN_STEP, messages=msg_base
    )

    # different user_id => miss
    msg_uid = [
        {
            "role": "system",
            "content": "sys1",
            "user_id": "u2",
            "plan_id": "p1",
            "topic_slug": "t1",
            "step_idx": 1,
        },
        {"role": "user", "content": "u1"},
    ]
    await gpt_client.create_learning_chat_completion(
        task=LLMTask.EXPLAIN_STEP, messages=msg_uid
    )

    # different plan_id => miss
    msg_plan = [
        {
            "role": "system",
            "content": "sys1",
            "user_id": "u1",
            "plan_id": "p2",
            "topic_slug": "t1",
            "step_idx": 1,
        },
        {"role": "user", "content": "u1"},
    ]
    await gpt_client.create_learning_chat_completion(
        task=LLMTask.EXPLAIN_STEP, messages=msg_plan
    )

    # different topic_slug => miss
    msg_topic = [
        {
            "role": "system",
            "content": "sys1",
            "user_id": "u1",
            "plan_id": "p1",
            "topic_slug": "t2",
            "step_idx": 1,
        },
        {"role": "user", "content": "u1"},
    ]
    await gpt_client.create_learning_chat_completion(
        task=LLMTask.EXPLAIN_STEP, messages=msg_topic
    )

    # different step_idx => miss
    msg_step = [
        {
            "role": "system",
            "content": "sys1",
            "user_id": "u1",
            "plan_id": "p1",
            "topic_slug": "t1",
            "step_idx": 2,
        },
        {"role": "user", "content": "u1"},
    ]
    await gpt_client.create_learning_chat_completion(
        task=LLMTask.EXPLAIN_STEP, messages=msg_step
    )

    assert call_count == 8


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
    monkeypatch.setattr(gpt_client, "choose_model", lambda task: "m1")
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
    monkeypatch.setattr(gpt_client, "choose_model", lambda task: "m1")
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
    assert get_metric_value(learning_prompt_cache_hit) == 1
    assert get_metric_value(learning_prompt_cache_miss) == 1
    monkeypatch.setattr(gpt_client.time, "time", lambda: start + 2)
    await gpt_client.create_learning_chat_completion(task=LLMTask.EXPLAIN_STEP, messages=messages)
    assert call_count == 2
    assert get_metric_value(learning_prompt_cache_miss) == 2
