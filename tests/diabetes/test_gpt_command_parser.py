from __future__ import annotations

from typing import Any
import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
from services.api.app.diabetes import gpt_command_parser  # noqa: E402


def test_extract_first_json_in_code_block() -> None:
    text = (
        "Ответ:\n"
        "```json\n"
        '{"action":"add_entry","time":"07:00","fields":{}}\n'
        "```"
    )
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "time": "07:00",
        "fields": {},
    }


def test_extract_first_json_nested_structures() -> None:
    text = (
        '{"outer":{"inner":[{"foo":1},' '{"action":"delete_entry","fields":{"id":5}}]}}'
    )
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "delete_entry",
        "fields": {"id": 5},
    }


def test_extract_first_json_no_command() -> None:
    assert gpt_command_parser._extract_first_json("Просто текст без команд") is None


class FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = type("Msg", (), {"content": content})()


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [FakeChoice(content)]


@pytest.mark.asyncio
async def test_parse_command_with_code_block(monkeypatch: pytest.MonkeyPatch) -> None:
    response = FakeResponse(
        "Вот команда:\n```json\n" '{"action":"add_entry","fields":{}}\n```'
    )

    async def fake_create(*args: Any, **kwargs: Any) -> FakeResponse:
        return response

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", fake_create)

    result = await gpt_command_parser.parse_command("test")
    assert result == {"action": "add_entry", "fields": {}}


@pytest.mark.asyncio
async def test_parse_command_without_json(monkeypatch: pytest.MonkeyPatch) -> None:
    response = FakeResponse("Ответ без json и команд")

    async def fake_create(*args: Any, **kwargs: Any) -> FakeResponse:
        return response

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", fake_create)

    result = await gpt_command_parser.parse_command("test")
    assert result is None
