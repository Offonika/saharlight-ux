from __future__ import annotations

import logging

import pytest

from services.api.app.diabetes import learning_handlers


@pytest.mark.asyncio
async def test_generate_step_text_logged(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Ensure debug logging emits expected fields."""

    monkeypatch.setenv("LEARNING_DEBUG", "1")
    monkeypatch.setattr(learning_handlers, "debug", True)
    monkeypatch.setattr(
        learning_handlers, "build_system_prompt", lambda p, task=None: "sys"
    )
    monkeypatch.setattr(
        learning_handlers, "build_user_prompt_step", lambda slug, idx, prev: "usr"
    )

    async def fake_generate_step_text(*args: object, **kwargs: object) -> str:
        return "resp"

    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )
    monkeypatch.setattr(
        learning_handlers,
        "choose_model",
        lambda task: "m",
    )

    caplog.set_level(logging.INFO)

    result = await learning_handlers._generate_step_text_logged(
        {},
        "topic",
        2,
        "prev",
        user_id=1,
        plan_id=42,
        last_sent_step_id=5,
    )

    assert result == "resp"

    before = [r for r in caplog.records if r.msg == "learning_debug_before_llm"]
    after = [r for r in caplog.records if r.msg == "learning_debug_after_llm"]
    assert before and after

    rec = before[0]
    assert rec.user_id == 1
    assert rec.plan_id == 42
    assert rec.topic_slug == "topic"
    assert rec.step_idx == 2
    assert rec.last_sent_step_id == 5
    assert rec.sys_h == learning_handlers._sha1("sys")[:12]
    assert rec.usr_h == learning_handlers._sha1("usr")[:12]

    old_key = learning_handlers.make_cache_key("m", "sys", "usr", "", "", "", None, "")
    new_key = learning_handlers.make_cache_key(
        "m", "sys", "usr", "1", "42", "topic", 2, ""
    )
    assert rec.cache_key_old_preview == learning_handlers._sha1("|".join(old_key))[:12]
    assert rec.cache_key_new_preview == learning_handlers._sha1("|".join(new_key))[:12]

    rec_after = after[0]
    assert rec_after.pending_step_id == 2
    assert rec_after.reply_preview == "resp"
