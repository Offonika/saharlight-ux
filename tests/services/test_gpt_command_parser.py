import os
import asyncio
import time
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
from diabetes.utils import openai_utils  # noqa: F401,E402
from diabetes import gpt_command_parser  # noqa: E402


@pytest.mark.asyncio
async def test_parse_command_timeout_non_blocking(monkeypatch):
    def slow_create(*args, **kwargs):
        time.sleep(1)

        class FakeResponse:
            choices = [
                type("Choice", (), {"message": type("Msg", (), {"content": "{}"})()})
            ]

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


@pytest.mark.asyncio
async def test_parse_command_with_array_response(monkeypatch):
    class FakeResponse:
        choices = [
            type(
                "Choice",
                (),
                {"message": type("Msg", (), {"content": "[{\"action\":\"add_entry\"}]"})()},
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

    assert result is None


@pytest.mark.asyncio
async def test_parse_command_with_scalar_response(monkeypatch):
    class FakeResponse:
        choices = [
            type(
                "Choice",
                (),
                {"message": type("Msg", (), {"content": "42"})()},
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

    assert result is None


@pytest.mark.parametrize(
    "token",
    [
        "sk-" + "A1b2_" * 8 + "Z9",
        "ghp_" + "A1b2" * 9 + "Cd",
    ],
)
def test_sanitize_masks_api_like_tokens(token):
    text = f"before {token} after"
    assert (
        gpt_command_parser._sanitize_sensitive_data(text)
        == "before [REDACTED] after"
    )


def test_sanitize_leaves_numeric_strings():
    number = "1234567890" * 4 + "12"
    text = f"id {number}"
    assert gpt_command_parser._sanitize_sensitive_data(text) == text
