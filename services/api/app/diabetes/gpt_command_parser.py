import asyncio
import json
import logging
import re

from openai import OpenAIError
from openai.types.chat import ChatCompletion

from pydantic import ValidationError

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
    "// xe, carbs_g, dose, sugar_before и пр.\n"
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


API_KEY_RE = re.compile(
    r"\b(?=[A-Za-z0-9_-]*[a-z])"
    r"(?=[A-Za-z0-9_-]*[A-Z])"
    r"(?=[A-Za-z0-9_-]*\d)"
    r"[A-Za-z0-9_-]{40,}\b"
)


def _sanitize_sensitive_data(text: str) -> str:
    """Mask potentially sensitive tokens in *text* before logging."""
    return API_KEY_RE.sub("[REDACTED]", text)


def _extract_first_json(text: str) -> dict[str, object] | None:
    """Return the first standalone JSON object in *text* or ``None``."""

    decoder = json.JSONDecoder()
    search_start = 0
    while True:
        start = text.find("{", search_start)
        if start == -1:
            break

        # If the object is preceded by ``[``, treat it as part of an array and
        # skip it so that we don't parse array responses like ``[{...}]``.
        if text[:start].rstrip().endswith("["):
            search_start = start + 1
            continue

        try:
            obj, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError as exc:  # pragma: no cover - simple fallback
            search_start = exc.pos + 1
            continue
        if isinstance(obj, dict):
            return obj
        search_start = start + 1

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
        nested ``fields`` describing the command, or ``None`` if parsing fails.
    """

    try:
        # ``asyncio.to_thread`` runs the blocking OpenAI client in the event
        # loop's shared thread pool, so we reuse threads instead of spawning a
        # fresh ``ThreadPoolExecutor`` for every invocation.
        response: ChatCompletion = await asyncio.wait_for(
            asyncio.to_thread(
                create_chat_completion,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0,
                max_tokens=256,
                timeout=timeout,
            ),
            timeout,
        )
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
    logger.info("GPT raw response: %s", safe_content[:200])
    parsed = _extract_first_json(content)
    if parsed is None:
        logger.error("No JSON object found in response")
        return None
    try:
        return CommandSchema.model_validate(parsed).model_dump(exclude_none=True)
    except ValidationError:
        logger.exception("Invalid command structure")
        return None
