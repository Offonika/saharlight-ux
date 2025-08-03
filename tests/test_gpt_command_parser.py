import asyncio
import os
import time
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
from diabetes import openai_utils  # noqa: F401
from diabetes import gpt_command_parser


@pytest.mark.asyncio
async def test_parse_command_timeout_non_blocking(monkeypatch):
    def slow_create(*args, **kwargs):
        time.sleep(1)
        class FakeResponse:
            choices = [type("Choice", (), {"message": type("Msg", (), {"content": "{}"})()})]
        return FakeResponse()

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=slow_create))
    )
    monkeypatch.setattr(gpt_command_parser, "_get_client", lambda: fake_client)

    start = time.perf_counter()
    result, _ = await asyncio.gather(
        gpt_command_parser.parse_command("test", timeout=0.1),
        asyncio.sleep(0.1),
    )
    elapsed = time.perf_counter() - start

    assert result is None
    assert elapsed < 0.5


@pytest.mark.asyncio
async def test_parse_command_with_explanatory_text(monkeypatch):
    class FakeResponse:
        choices = [
            type(
                "Choice",
                (),
                {
                    "message": type(
                        "Msg",
                        (),
                        {
                            "content": (
                                "Вот ответ: {\"action\":\"add_entry\","
                                "\"time\":\"09:00\",\"fields\":{}}"
                                " Дополнительный текст"
                            )
                        },
                    )()
                },
            )
        ]

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda *args, **kwargs: FakeResponse()
            )
        )
    )
    monkeypatch.setattr(gpt_command_parser, "_get_client", lambda: fake_client)

    result = await gpt_command_parser.parse_command("test")

    assert result == {"action": "add_entry", "time": "09:00", "fields": {}}
