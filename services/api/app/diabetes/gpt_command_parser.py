import asyncio
import json
import logging
import re
from collections import deque
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

ACTIONS_REQUIRE_FIELDS: set[str] = {"add_entry", "update_entry"}

MAX_JSON_CHARS = 10_000


def _sanitize_sensitive_data(text: str) -> str:
    """Mask potentially sensitive tokens in *text* before logging."""
    return API_KEY_RE.sub("[REDACTED]", text)


def _extract_first_json(text: str) -> dict[str, object] | None:
    """Return the first JSON dictionary found in *text*.

    The function walks through *text* while counting curly and square brackets
    outside of string literals. Whenever a balanced JSON segment is found, it is
    parsed with :func:`json.loads` and searched breadth‑first for the first
    dictionary, preferring one that contains an ``"action"`` key. At most
    ``MAX_JSON_CHARS`` characters are inspected; if the limit is reached without
    finding a dictionary, ``None`` is returned.
    """

    length = min(len(text), MAX_JSON_CHARS)
    i = 0
    in_str = False
    escape = False
    quote = ""
    start = -1
    braces = 0
    brackets = 0
    saw_closing = False

    def search_dict(obj: object) -> dict[str, object] | None:
        queue: deque[object] = deque([obj])
        first_dict: dict[str, object] | None = None
        while queue:
            current = queue.popleft()
            if isinstance(current, dict):
                if first_dict is None:
                    first_dict = current
                if "action" in current:
                    return current
                queue.extend(current.values())
            elif isinstance(current, list):
                queue.extend(current)
        return first_dict

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
        if ch == '{' or ch == '[':
            if braces == 0 and brackets == 0:
                start = i
            if ch == '{':
                braces += 1
            else:
                brackets += 1
        elif ch == '}' or ch == ']':
            saw_closing = True
            if ch == '}' and braces > 0:
                braces -= 1
            elif ch == ']' and brackets > 0:
                brackets -= 1
            else:
                start = -1
                braces = 0
                brackets = 0
                i += 1
                continue
            if braces == 0 and brackets == 0 and start != -1:
                segment = text[start : i + 1]
                try:
                    obj = json.loads(segment)
                except json.JSONDecodeError:
                    saw_closing = True
                    start += 1
                    i = start
                    braces = 0
                    brackets = 0
                    continue
                found = search_dict(obj)
                if found is not None:
                    return found
                start = -1
        i += 1

    if start != -1:
        return {} if saw_closing else None
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
    if cmd.action in ACTIONS_REQUIRE_FIELDS and "fields" not in cmd_dict:
        logger.error("Missing fields for action=%s", cmd.action)
        return None
    return cmd_dict
