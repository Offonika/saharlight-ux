import asyncio

import pytest
from openai import OpenAIError

from services.api.app.diabetes import gpt_command_parser


@pytest.mark.anyio
async def test_parse_command_handles_asyncio_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_timeout(*args: object, **kwargs: object) -> None:
        raise asyncio.TimeoutError

    monkeypatch.setattr(
        gpt_command_parser, "create_chat_completion", raise_timeout
    )

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.anyio
async def test_parse_command_handles_openai_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_openai(*args: object, **kwargs: object) -> None:
        raise OpenAIError("boom")

    monkeypatch.setattr(
        gpt_command_parser, "create_chat_completion", raise_openai
    )

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.anyio
async def test_parse_command_handles_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_value(*args: object, **kwargs: object) -> None:
        raise ValueError

    monkeypatch.setattr(
        gpt_command_parser, "create_chat_completion", raise_value
    )

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.anyio
async def test_parse_command_handles_type_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_type(*args: object, **kwargs: object) -> None:
        raise TypeError

    monkeypatch.setattr(
        gpt_command_parser, "create_chat_completion", raise_type
    )

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.anyio
async def test_parse_command_returns_none_without_choices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NoChoices:
        pass

    def create(*args: object, **kwargs: object) -> NoChoices:
        return NoChoices()

    monkeypatch.setattr(
        gpt_command_parser, "create_chat_completion", create
    )

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.anyio
async def test_parse_command_returns_none_without_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NoMessageResponse:
        choices = [type("Choice", (), {})()]

    def create(*args: object, **kwargs: object) -> NoMessageResponse:
        return NoMessageResponse()

    monkeypatch.setattr(
        gpt_command_parser, "create_chat_completion", create
    )

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.anyio
async def test_parse_command_returns_none_without_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NoContentResponse:
        choices = [type("Choice", (), {"message": type("Msg", (), {})()})]

    def create(*args: object, **kwargs: object) -> NoContentResponse:
        return NoContentResponse()

    monkeypatch.setattr(
        gpt_command_parser, "create_chat_completion", create
    )

    result = await gpt_command_parser.parse_command("test")

    assert result is None


def test_sanitize_sensitive_data_masks_token() -> None:
    token = "sk-" + "A1b2" * 10
    text = f"key {token} end"
    assert (
        gpt_command_parser._sanitize_sensitive_data(text)
        == "key [REDACTED] end"
    )


def test_extract_first_json_ignores_array() -> None:
    text = '[{"action":"add_entry"}]'
    assert gpt_command_parser._extract_first_json(text) is None


def test_extract_first_json_malformed_json() -> None:
    text = '{"action":"add_entry"'
    assert gpt_command_parser._extract_first_json(text) is None
