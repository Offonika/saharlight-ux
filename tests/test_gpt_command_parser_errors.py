import asyncio
import logging

import pytest
from openai import OpenAIError

from services.api.app.diabetes import gpt_command_parser


@pytest.mark.asyncio
async def test_parse_command_handles_asyncio_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def raise_timeout(*args: object, **kwargs: object) -> None:
        raise asyncio.TimeoutError

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", raise_timeout)

    with pytest.raises(gpt_command_parser.ParserTimeoutError):
        await gpt_command_parser.parse_command("test")


@pytest.mark.asyncio
async def test_parse_command_handles_openai_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def raise_openai(*args: object, **kwargs: object) -> None:
        raise OpenAIError("boom")

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", raise_openai)

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.asyncio
async def test_parse_command_handles_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def raise_value(*args: object, **kwargs: object) -> None:
        raise ValueError

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", raise_value)

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.asyncio
async def test_parse_command_handles_type_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def raise_type(*args: object, **kwargs: object) -> None:
        raise TypeError

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", raise_type)

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.asyncio
async def test_parse_command_returns_none_without_choices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NoChoices:
        pass

    async def create(*args: object, **kwargs: object) -> NoChoices:
        return NoChoices()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.asyncio
async def test_parse_command_returns_none_without_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NoMessageResponse:
        choices = [type("Choice", (), {})()]

    async def create(*args: object, **kwargs: object) -> NoMessageResponse:
        return NoMessageResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.asyncio
async def test_parse_command_returns_none_without_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NoContentResponse:
        choices = [type("Choice", (), {"message": type("Msg", (), {})()})]

    async def create(*args: object, **kwargs: object) -> NoContentResponse:
        return NoContentResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.asyncio
async def test_parse_command_empty_content(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class EmptyContentResponse:
        choices = [type("Choice", (), {"message": type("Msg", (), {"content": ""})()})]

    async def create(*args: object, **kwargs: object) -> EmptyContentResponse:
        return EmptyContentResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    with caplog.at_level(logging.ERROR):
        result = await gpt_command_parser.parse_command("test")

    assert result is None
    assert "Content is empty in GPT response" in caplog.text


@pytest.mark.asyncio
async def test_parse_command_non_string_content(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class NonStringContentResponse:
        choices = [type("Choice", (), {"message": type("Msg", (), {"content": 123})()})]

    async def create(*args: object, **kwargs: object) -> NonStringContentResponse:
        return NonStringContentResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    with caplog.at_level(logging.ERROR):
        result = await gpt_command_parser.parse_command("test")

    assert result is None
    assert "Content is not a string in GPT response" in caplog.text


@pytest.mark.asyncio
async def test_parse_command_string_without_json(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class NoJsonResponse:
        choices = [
            type(
                "Choice",
                (),
                {"message": type("Msg", (), {"content": "hello"})()},
            )
        ]

    async def create(*args: object, **kwargs: object) -> NoJsonResponse:
        return NoJsonResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    with caplog.at_level(logging.ERROR):
        result = await gpt_command_parser.parse_command("test")

    assert result is None
    assert "No JSON object found in response" in caplog.text


@pytest.mark.asyncio
async def test_parse_command_json_invalid_structure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class BadStructureResponse:
        choices = [
            type(
                "Choice",
                (),
                {"message": type("Msg", (), {"content": '{"action": "add_entry"}'})()},
            )
        ]

    async def create(*args: object, **kwargs: object) -> BadStructureResponse:
        return BadStructureResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    with caplog.at_level(logging.ERROR):
        result = await gpt_command_parser.parse_command("test")

    assert result is None
    assert "Missing fields for action=add_entry" in caplog.text


def test_sanitize_sensitive_data_masks_token() -> None:
    token = "sk-" + "A1b2" * 10
    text = f"key {token} end"
    assert gpt_command_parser._sanitize_sensitive_data(text) == "key [REDACTED] end"


def test_extract_first_json_array_single_dict() -> None:
    text = '[{"action":"add_entry","fields":{}}]'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_malformed_json() -> None:
    text = '{"action":"add_entry"'
    assert gpt_command_parser._extract_first_json(text) is None
