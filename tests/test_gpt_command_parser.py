from typing import Any

import os
import asyncio
import time
import logging

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
from services.api.app.diabetes.utils import openai_utils  # noqa: F401,E402
from services.api.app.diabetes import gpt_command_parser  # noqa: E402


@pytest.mark.asyncio
async def test_parse_command_timeout_non_blocking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def slow_create(*args: Any, **kwargs: Any) -> Any:
        time.sleep(1)

        class FakeResponse:
            choices = [
                type("Choice", (), {"message": type("Msg", (), {"content": "{}"})()})
            ]

        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", slow_create)

    start = time.perf_counter()
    result, _ = await asyncio.gather(
        gpt_command_parser.parse_command("test", timeout=0.1),
        asyncio.sleep(0.1),
    )
    elapsed = time.perf_counter() - start

    assert result is None
    assert elapsed < 0.5


@pytest.mark.asyncio
async def test_parse_command_with_explanatory_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                                'Вот ответ: {"action":"add_entry",'
                                '"time":"09:00","fields":{}}'
                                " Дополнительный текст"
                            )
                        },
                    )()
                },
            )
        ]

    def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result == {"action": "add_entry", "time": "09:00", "fields": {}}


@pytest.mark.asyncio
async def test_parse_command_with_array_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        choices = [
            type(
                "Choice",
                (),
                {"message": type("Msg", (), {"content": '[{"action":"add_entry"}]'})()},
            )
        ]

    def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.asyncio
async def test_parse_command_with_multiple_json_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                                '{"action":"add_entry","time":"09:00","fields":{}} '
                                '{"action":"update_profile","fields":{}}'
                            )
                        },
                    )()
                },
            )
        ]

    def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result == {"action": "add_entry", "time": "09:00", "fields": {}}


@pytest.mark.asyncio
async def test_parse_command_with_nested_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                                'prefix {"action":"add_entry","fields":{"nested":{"a":1},"note":"смесь {сахара}"}} suffix'
                            )
                        },
                    )()
                },
            )
        ]

    def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result == {
        "action": "add_entry",
        "fields": {"nested": {"a": 1}, "note": "смесь {сахара}"},
    }


@pytest.mark.asyncio
async def test_parse_command_with_scalar_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        choices = [
            type(
                "Choice",
                (),
                {"message": type("Msg", (), {"content": "42"})()},
            )
        ]

    def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.asyncio
async def test_parse_command_with_invalid_schema(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class FakeResponse:
        choices = [
            type(
                "Choice",
                (),
                {
                    "message": type(
                        "Msg",
                        (),
                        {"content": '{"action":123,"time":"09:00","fields":{}}'},
                    )()
                },
            )
        ]

    def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    with caplog.at_level(logging.ERROR):
        result = await gpt_command_parser.parse_command("test")

    assert result is None
    assert "Invalid command structure" in caplog.text


@pytest.mark.asyncio
async def test_parse_command_with_missing_content(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class FakeResponse:
        choices = [type("Choice", (), {"message": type("Msg", (), {})()})]

    def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    with caplog.at_level(logging.ERROR):
        result = await gpt_command_parser.parse_command("test")

    assert result is None
    assert "No content in GPT response" in caplog.text


@pytest.mark.asyncio
async def test_parse_command_with_non_string_content(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class FakeResponse:
        choices = [
            type(
                "Choice",
                (),
                {"message": type("Msg", (), {"content": 123})()},
            )
        ]

    def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    with caplog.at_level(logging.ERROR):
        result = await gpt_command_parser.parse_command("test")

    assert result is None
    assert "Content is not a string in GPT response" in caplog.text


@pytest.mark.asyncio
async def test_parse_command_propagates_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def bad_create(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", bad_create)

    with pytest.raises(RuntimeError, match="boom"):
        await gpt_command_parser.parse_command("test")


@pytest.mark.parametrize(
    "token",
    [
        "sk-" + "A1b2_" * 8 + "Z9",
        "ghp_" + "A1b2" * 9 + "Cd",
    ],
)
def test_sanitize_masks_api_like_tokens(token: Any) -> None:
    text = f"before {token} after"
    assert (
        gpt_command_parser._sanitize_sensitive_data(text) == "before [REDACTED] after"
    )


def test_sanitize_leaves_numeric_strings() -> None:
    number = "1234567890" * 4 + "12"
    text = f"id {number}"
    assert gpt_command_parser._sanitize_sensitive_data(text) == text


def test_extract_first_json_multiple_objects() -> None:
    text = '{"action":"add_entry","fields":{}} ' '{"action":"delete_entry","fields":{}}'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_malformed_input() -> None:
    text = '{"action":"add_entry","fields":{}'
    assert gpt_command_parser._extract_first_json(text) is None


@pytest.mark.asyncio
async def test_parse_command_with_multiple_jsons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                                '{"action":"add_entry","fields":{}} '
                                '{"action":"delete_entry","fields":{}}'
                            )
                        },
                    )()
                },
            )
        ]

    def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result == {"action": "add_entry", "fields": {}}


@pytest.mark.asyncio
async def test_parse_command_with_malformed_json(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class FakeResponse:
        choices = [
            type(
                "Choice",
                (),
                {
                    "message": type(
                        "Msg",
                        (),
                        {"content": '{"action":"add_entry","fields":{}'},
                    )()
                },
            )
        ]

    def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    with caplog.at_level(logging.ERROR):
        result = await gpt_command_parser.parse_command("test")

    assert result is None
    assert "No JSON object found in response" in caplog.text
