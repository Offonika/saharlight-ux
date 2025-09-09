from typing import Any
from types import SimpleNamespace

import os
import asyncio
import time
import logging

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
from services.api.app import config  # noqa: E402
from services.api.app.diabetes.utils import openai_utils  # noqa: F401,E402
from services.api.app.diabetes import gpt_command_parser  # noqa: E402


@pytest.mark.asyncio
async def test_parse_command_timeout_non_blocking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def slow_create(*args: Any, **kwargs: Any) -> Any:
        started.set()
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            cancelled.set()
            raise

        class FakeResponse:
            choices = [
                type("Choice", (), {"message": type("Msg", (), {"content": "{}"})()})
            ]

        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", slow_create)

    start = time.perf_counter()
    results = await asyncio.gather(
        gpt_command_parser.parse_command("test", timeout=0.1),
        asyncio.sleep(0.1),
        return_exceptions=True,
    )
    elapsed = time.perf_counter() - start

    assert isinstance(results[0], gpt_command_parser.ParserTimeoutError)
    assert elapsed < 0.5
    assert started.is_set()
    await asyncio.sleep(0.2)
    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_parse_command_with_explanatory_text(
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

    captured: dict[str, Any] = {}

    async def create(*args: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    with caplog.at_level(logging.DEBUG):
        result = await gpt_command_parser.parse_command("test")

    assert result == {"action": "add_entry", "time": "09:00", "fields": {}}
    assert captured.get("model") == config.get_settings().openai_command_model
    assert "GPT raw response:" in caplog.text


@pytest.mark.asyncio
async def test_parse_command_with_array_response(
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
                        {"content": '[{"action":"add_entry","fields":{}}]'},
                    )()
                },
            )
        ]

    async def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")
    assert result == {"action": "add_entry", "fields": {}}


@pytest.mark.asyncio
async def test_parse_command_uses_config_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        choices = [
            type(
                "Choice",
                (),
                {
                    "message": type(
                        "Msg", (), {"content": '{"action":"get_day_summary"}'}
                    )()
                },
            )
        ]

    called: dict[str, Any] = {}

    async def create(*args: Any, **kwargs: Any) -> Any:
        called.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(openai_command_model="model-x"),
    )

    await gpt_command_parser.parse_command("test")

    assert called.get("model") == "model-x"


@pytest.mark.asyncio
async def test_parse_command_with_array_multiple_objects(
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
                                '[{"action":"add_entry","fields":{}},'
                                '{"action":"delete_entry","fields":{}}]'
                            )
                        },
                    )()
                },
            )
        ]

    async def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result is None


@pytest.mark.asyncio
async def test_parse_command_without_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        choices = [
            type(
                "Choice",
                (),
                {
                    "message": type(
                        "Msg", (), {"content": '{"action":"get_day_summary"}'}
                    )()
                },
            )
        ]

    async def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result == {"action": "get_day_summary"}


@pytest.mark.asyncio
async def test_parse_command_get_stats_without_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        choices = [
            type(
                "Choice",
                (),
                {"message": type("Msg", (), {"content": '{"action":"get_stats"}'})()},
            )
        ]

    async def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result == {"action": "get_stats"}


@pytest.mark.asyncio
async def test_parse_command_delete_entry_without_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        choices = [
            type(
                "Choice",
                (),
                {
                    "message": type(
                        "Msg", (), {"content": '{"action":"delete_entry"}'}
                    )()
                },
            )
        ]

    async def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result == {"action": "delete_entry"}


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

    async def create(*args: Any, **kwargs: Any) -> Any:
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
                                "prefix "
                                '{"action":"add_entry","fields":{"nested":{"a":1},'
                                '"note":"смесь {сахара}"}} '
                                "suffix"
                            )
                        },
                    )()
                },
            )
        ]

    async def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    result = await gpt_command_parser.parse_command("test")

    assert result == {
        "action": "add_entry",
        "fields": {"nested": {"a": 1}, "note": "смесь {сахара}"},
    }


@pytest.mark.asyncio
async def test_parse_command_with_braces_in_explanatory_text(
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
                                '"пример {текста}" '
                                '{"action":"add_entry","fields":{}}'
                                " trailing"
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

    async def create(*args: Any, **kwargs: Any) -> Any:
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

    async def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    with caplog.at_level(logging.ERROR):
        result = await gpt_command_parser.parse_command("test")

    assert result is None
    assert "Command validation failed for action=123" in caplog.text


@pytest.mark.asyncio
async def test_parse_command_with_missing_content(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class FakeResponse:
        choices = [type("Choice", (), {"message": type("Msg", (), {})()})]

    async def create(*args: Any, **kwargs: Any) -> Any:
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

    async def create(*args: Any, **kwargs: Any) -> Any:
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
    async def bad_create(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", bad_create)

    with pytest.raises(RuntimeError, match="boom"):
        await gpt_command_parser.parse_command("test")


@pytest.mark.parametrize(
    "token",
    [
        "sk-" + "A1b2_" * 8 + "Z9",
        "ghp_" + "A1b2" * 9 + "Cd",
        "sk-" + "A1b2" * 7 + "C",
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


def test_sanitize_masks_multiple_tokens() -> None:
    token1 = "sk-" + "A1b2_" * 8 + "Z9"
    token2 = "ghp_" + "A1b2" * 9 + "Cd"
    text = f"{token1} middle {token2}"
    assert (
        gpt_command_parser._sanitize_sensitive_data(text)
        == "[REDACTED] middle [REDACTED]"
    )


def test_sanitize_leaves_short_api_like_token() -> None:
    token = "sk-" + "A1b2" * 7
    text = f"before {token} after"
    assert gpt_command_parser._sanitize_sensitive_data(text) == text


def test_extract_first_json_array_single_object() -> None:
    text = '[{"action":"add_entry","fields":{}}]'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_multi_object_array() -> None:
    text = (
        '[{"action":"add_entry","fields":{}},' '{"action":"delete_entry","fields":{}}]'
    )
    assert gpt_command_parser._extract_first_json(text) is None


def test_extract_first_json_nested_object_wrapper() -> None:
    text = '{"wrapper":{"action":"add_entry","fields":{}}}'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_nested_array_wrapper() -> None:
    text = '[["noise"], [{"action":"add_entry","fields":{}}]]'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_multiple_objects() -> None:
    text = '{"action":"add_entry","fields":{}} ' '{"action":"delete_entry","fields":{}}'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_braces_in_string_before_object() -> None:
    text = 'prefix "not json { }" {"action":"add_entry","fields":{}}'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_braces_in_single_quotes_before_object() -> None:
    text = "prefix 'not json { [ ] }' " '{"action":"add_entry","fields":{}}'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_explanatory_braces_before_object() -> None:
    text = "text with {not valid json} " '{"action":"add_entry","fields":{}}'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_multiple_objects_no_space() -> None:
    text = '{"action":"add_entry","fields":{}}' '{"action":"delete_entry","fields":{}}'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_malformed_input() -> None:
    text = '{"action":"add_entry","fields":{}'
    assert gpt_command_parser._extract_first_json(text) == {}


def test_extract_first_json_simple_object() -> None:
    text = '{"action":"add_entry","fields":{}}'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_no_object() -> None:
    assert gpt_command_parser._extract_first_json("just some text without json") is None


def test_extract_first_json_with_escaped_quotes() -> None:
    text = (
        'prefix "escaped \\"quote\\"" '
        '{"action":"add_entry","fields":{"note":"He said \\"hi\\""}}'
    )
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {"note": 'He said "hi"'},
    }


def test_extract_first_json_array_with_many_objects() -> None:
    text = (
        '[{"action":"add_entry","fields":{}},' ' {"action":"delete_entry","fields":{}}]'
    )
    assert gpt_command_parser._extract_first_json(text) is None


def test_extract_first_json_malformed_then_valid() -> None:
    text = '{"bad":1] {"action":"add_entry","fields":{}}'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_non_dict_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    orig_raw_decode = gpt_command_parser.json.JSONDecoder.raw_decode

    def fake_raw_decode(
        self: gpt_command_parser.json.JSONDecoder, s: str, idx: int = 0
    ) -> tuple[object, int]:
        if s[idx:].startswith('{"skip":1}'):
            return 1, idx + len('{"skip":1}')
        return orig_raw_decode(self, s, idx)

    monkeypatch.setattr(
        gpt_command_parser.json.JSONDecoder, "raw_decode", fake_raw_decode
    )
    text = '{"skip":1} {"action":"add_entry","fields":{}}'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


def test_extract_first_json_nested_object() -> None:
    text = 'prefix {"action":"add_entry","fields":{"nested":{"level":1}}}' " suffix"
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {"nested": {"level": 1}},
    }


def test_extract_first_json_nested_array() -> None:
    text = 'prefix {"action":"add_entry","fields":{"list":[{"x":1},{"x":2}]}}' " suffix"
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {"list": [{"x": 1}, {"x": 2}]},
    }


def test_extract_first_json_with_escaped_chars() -> None:
    text = 'start {"action":"add_entry","fields":{"note":"Line1\\nLine2\\\\"}} end'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {"note": "Line1\nLine2\\"},
    }


def test_extract_first_json_braces_inside_string_field() -> None:
    text = (
        'prefix {"action":"add_entry","fields":{"note":"use {curly} braces"}} ' "suffix"
    )
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {"note": "use {curly} braces"},
    }


def test_extract_first_json_braces_and_quotes_inside_string_field() -> None:
    text = '{"action":"add_entry","fields":{"note":"{\\"inner\\":1} end"}}'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {"note": '{"inner":1} end'},
    }


def test_extract_first_json_deep_nested_arrays() -> None:
    text = (
        'start {"action":"add_entry","fields":{"matrix":[[1,2],[3,{"v":[4,5]}]]}}'
        " end"
    )
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {"matrix": [[1, 2], [3, {"v": [4, 5]}]]},
    }


def test_extract_first_json_quotes_inside_value() -> None:
    text = '{"action":"add_entry","fields":{"note":"He said \\"Hello\\""}}'
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {"note": 'He said "Hello"'},
    }


def test_extract_first_json_three_objects_in_row() -> None:
    text = (
        '{"action":"add_entry","fields":{}}'
        '{"action":"delete_entry","fields":{}}'
        '{"action":"update_entry","fields":{}}'
    )
    assert gpt_command_parser._extract_first_json(text) == {
        "action": "add_entry",
        "fields": {},
    }


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

    async def create(*args: Any, **kwargs: Any) -> Any:
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

    async def create(*args: Any, **kwargs: Any) -> Any:
        return FakeResponse()

    monkeypatch.setattr(gpt_command_parser, "create_chat_completion", create)

    with caplog.at_level(logging.ERROR):
        result = await gpt_command_parser.parse_command("test")

    assert result is None
    assert "Command validation failed" in caplog.text
