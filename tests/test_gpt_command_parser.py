import asyncio
import os
import time
import pytest

os.environ.setdefault("OPENAI_API_KEY", "test")
from diabetes import gpt_command_parser


@pytest.mark.asyncio
async def test_parse_command_timeout_non_blocking(monkeypatch):
    def slow_create(*args, **kwargs):
        time.sleep(1)
        class FakeResponse:
            choices = [type("Choice", (), {"message": type("Msg", (), {"content": "{}"})()})]
        return FakeResponse()

    monkeypatch.setattr(
        gpt_command_parser.client.chat.completions,
        "create",
        slow_create,
    )

    start = time.perf_counter()
    result, _ = await asyncio.gather(
        gpt_command_parser.parse_command("test", timeout=0.1),
        asyncio.sleep(0.1),
    )
    elapsed = time.perf_counter() - start

    assert result is None
    assert elapsed < 0.5
