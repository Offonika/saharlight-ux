import asyncio
import json
import logging
import re
from collections.abc import Awaitable
from typing import cast

from openai import OpenAIError
from openai.types.chat import ChatCompletion

from pydantic import ValidationError

from services.api.app import config
from services.api.app.diabetes.services.gpt_client import create_chat_completion
from services.api.app.schemas import CommandSchema

logger = logging.getLogger(__name__)


class ParserTimeoutError(Exception):
    """Raised when GPT parsing exceeds the allotted *timeout*."""


# Prompt guiding GPT to convert free-form diary text into a single JSON command
SYSTEM_PROMPT = (
    "Ты — парсер дневника диабетика.\n"
    "Из свободного текста пользователя извлеки команду и верни СТРОГО ОДИН "
    "JSON‑объект без пояснений.\n\n"
    "Формат:\n"
    "{\n"
    '  "action": "add_entry" | "update_entry" | "delete_entry" | '
    '"update_profile" | "set_reminder" | "get_stats" | "get_day_summary",\n'
    '  "entry_date": "YYYY-MM-DDTHH:MM:SS",      '
    "// ⇦ указывай ТОЛЬКО если есть полная дата\n"
    '  "time": "HH:MM",                          '
    "// ⇦ если в сообщении было лишь время\n"
    '  "fields": { ... }                         '
    "// параметры (xe, carbs_g, dose, sugar_before и др.); "
    "если они не нужны — опусти это поле\n"
    "}\n\n"
    "📌  Правила временных полей:\n"
    "•  Если пользователь назвал только время (напр. «в 9:00») — заполни поле "
    '"time", а «entry_date» НЕ добавляй.\n'
    "•  Слова «сегодня», «вчера» игнорируй — бот сам подставит дату.\n"
    "•  Если в сообщении указаны день/месяц/год — запиши их в "
    '"entry_date" в формате ISO 8601 (YYYY‑MM‑DDTHH:MM:SS) и НЕ пиши поле '
    '"time".\n'
    "•  Часы и минуты всегда с ведущими нулями (09:00).\n\n"
    "Пример 1 (только время):\n"
    '  {"action":"add_entry","time":"09:00",'
    '"fields":{"xe":5,"dose":10,"sugar_before":15}}\n'
    "Пример 2 (полная дата):\n"
    '  {"action":"add_entry","entry_date":"2025-05-04T20:00:00",'
    '"fields":{"carbs_g":60,"dose":6}}\n'
)


API_KEY_MIN_LENGTH = config.get_settings().api_key_min_length

API_KEY_RE = re.compile(
    r"\b(?=[A-Za-z0-9_-]*[a-z])"
    r"(?=[A-Za-z0-9_-]*[A-Z])"
    r"(?=[A-Za-z0-9_-]*\d)"
    rf"[A-Za-z0-9_-]{{{API_KEY_MIN_LENGTH},}}\b"
)


def _sanitize_sensitive_data(text: str) -> str:
    """Mask potentially sensitive tokens in *text* before logging."""
    return API_KEY_RE.sub("[REDACTED]", text)


def _extract_first_json(text: str) -> dict[str, object] | None:
    """Return the first complete JSON object found in *text*.

    The function iterates over *text* character by character keeping track of
    string literals and escape sequences.  This allows it to correctly ignore
    braces that appear inside quoted strings and extract the first JSON object
    or a single dictionary within a top-level array.  Other structures are
    skipped.
    """

    length = len(text)
    i = 0
    in_str = False
    escape = False
    quote = ""

    while i < length:
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_str = False
            i += 1
            continue
        if ch in {'"', "'"}:
            in_str = True
            quote = ch
            i += 1
            continue
        if ch not in "{[":
            i += 1
            continue
        if i > 0 and text[i - 1] not in " \t\r\n,[":
            i += 1
            continue

        start = i
        stack: list[str] = [ch]
        i += 1
        inner_in_str = False
        inner_escape = False
        inner_quote = ""

        while i < length and stack:
            c = text[i]
            if inner_in_str:
                if inner_escape:
                    inner_escape = False
                elif c == "\\":
                    inner_escape = True
                elif c == inner_quote:
                    inner_in_str = False
            else:
                if c in {'"', "'"}:
                    inner_in_str = True
                    inner_quote = c
                elif c in "{[":
                    stack.append(c)
                elif c == "}" and stack[-1] == "{":
                    stack.pop()
                elif c == "]" and stack[-1] == "[":
                    stack.pop()
            i += 1

        if stack:
            i = start + 1
            continue

        candidate = text[start:i]
        try:
            obj = cast(object, json.loads(candidate))
        except json.JSONDecodeError:
            i = start + 1
            continue
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, list):
            if len(obj) == 1 and isinstance(obj[0], dict):
                return obj[0]
            continue

    return None


async def parse_command(text: str, timeout: float = 10) -> dict[str, object] | None:
    """Parse *text* with GPT and return a command dictionary.

    Parameters
    ----------
    text:
        Free-form diary message that should be interpreted.
    timeout:
        Maximum time in seconds to wait for the OpenAI response.

    Returns
    -------
    dict[str, object] | None
        A dictionary with keys like ``action``, ``entry_date`` or ``time`` and
        optional ``fields`` describing the command, or ``None`` if parsing fails.
    """

    try:
        resp: ChatCompletion | Awaitable[ChatCompletion] = create_chat_completion(
            model=config.get_settings().openai_command_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0,
            max_tokens=256,
            timeout=timeout,
        )
        try:
            response: ChatCompletion = await asyncio.wait_for(
                cast(Awaitable[ChatCompletion], resp), timeout
            )
        except TypeError:
            if isinstance(resp, Awaitable):
                raise
            response = resp  # sync stub
    except asyncio.TimeoutError as exc:
        logger.error("Command parsing timed out")
        raise ParserTimeoutError from exc
    except OpenAIError:
        logger.exception("Command parsing failed")
        return None
    except ValueError:
        logger.exception("Invalid value during command parsing")
        return None
    except TypeError:
        logger.exception("Invalid type during command parsing")
        return None

    choices = getattr(response, "choices", None)
    if not choices:
        logger.error("No choices in GPT response")
        return None

    first = choices[0]
    message = getattr(first, "message", None)
    if message is None:
        logger.error("No message in first choice")
        return None

    content = getattr(message, "content", None)
    if content is None:
        logger.error("No content in GPT response")
        return None
    if not isinstance(content, str):
        logger.error("Content is not a string in GPT response")
        return None
    content = content.strip()
    if not content:
        logger.error("Content is empty in GPT response")
        return None

    safe_content = _sanitize_sensitive_data(content)
    logger.debug("GPT raw response: %s", safe_content[:200])
    parsed = _extract_first_json(content)
    if parsed is None:
        logger.error("No JSON object found in response")
        return None
    try:
        cmd = CommandSchema.model_validate(parsed)
    except ValidationError:
        action = parsed.get("action") if isinstance(parsed, dict) else None
        logger.exception("Command validation failed for action=%s", action)
        return None
    cmd_dict = cmd.model_dump(exclude_none=True)
    if cmd.action != "get_day_summary" and "fields" not in cmd_dict:
        logger.error("Missing fields for action=%s", cmd.action)
        return None
    return cmd_dict
