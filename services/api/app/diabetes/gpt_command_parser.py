import asyncio
import json
import logging
import re
from typing import Any

from openai import OpenAIError
from openai.types.chat import ChatCompletion

from pydantic import ValidationError

from services.api.app.diabetes.services.gpt_client import _get_client
from services.api.app.schemas import CommandSchema

# Prompt guiding GPT to convert free-form diary text into a single JSON command
SYSTEM_PROMPT = (
    "Ты — парсер дневника диабетика.\n"
    "Из свободного текста пользователя извлеки команду и верни СТРОГО ОДИН "
    "JSON‑объект без пояснений.\n\n"

    "Формат:\n"
    "{\n"
    '  "action": "add_entry" | "update_entry" | "delete_entry" | '
    '"update_profile" | "set_reminder" | "get_stats" | "get_day_summary",\n'
    '  "entry_date": "YYYY-MM-DDTHH:MM:SS",      // ⇦ указывай ТОЛЬКО если есть полная дата\n'
    '  "time": "HH:MM",                          // ⇦ если в сообщении было лишь время\n'
    '  "fields": { ... }                         // xe, carbs_g, dose, sugar_before и пр.\n'
    "}\n\n"

    "📌  Правила временных полей:\n"
    "•  Если пользователь назвал только время (напр. «в 9:00») — заполни поле "
    "\"time\", а «entry_date» НЕ добавляй.\n"
    "•  Слова «сегодня», «вчера» игнорируй — бот сам подставит дату.\n"
    "•  Если в сообщении указаны день/месяц/год — запиши их в "
    "\"entry_date\" в формате ISO 8601 (YYYY‑MM‑DDTHH:MM:SS) и НЕ пиши поле "
    "\"time\".\n"
    "•  Часы и минуты всегда с ведущими нулями (09:00).\n\n"

    "Пример 1 (только время):\n"
    "  {\"action\":\"add_entry\",\"time\":\"09:00\","
    "\"fields\":{\"xe\":5,\"dose\":10,\"sugar_before\":15}}\n"
    "Пример 2 (полная дата):\n"
    "  {\"action\":\"add_entry\",\"entry_date\":\"2025-05-04T20:00:00\","
    "\"fields\":{\"carbs_g\":60,\"dose\":6}}\n"
)


def _sanitize_sensitive_data(text: str) -> str:
    """Mask potentially sensitive tokens in *text* before logging."""
    api_key_pattern = (
        r"\b(?=[A-Za-z0-9_-]*[a-z])"
        r"(?=[A-Za-z0-9_-]*[A-Z])"
        r"(?=[A-Za-z0-9_-]*\d)"
        r"[A-Za-z0-9_-]{40,}\b"
    )
    return re.sub(api_key_pattern, "[REDACTED]", text)


def _extract_first_json(text: str) -> dict[str, object] | None:
    """Return the first standalone JSON object in *text* or ``None``."""

    start = text.find("{")
    if start == -1:
        return None

    # If the object is preceded by ``[``, treat it as part of an array and
    # ignore it so that we don't parse array responses like ``[{...}]``.
    if text[:start].rstrip().endswith("["):
        return None

    brace_count = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0:
                    candidate = text[start : idx + 1]
                    try:
                        obj = json.loads(candidate)
                    except json.JSONDecodeError:
                        return None
                    return obj if isinstance(obj, dict) else None
    return None


async def parse_command(text: str, timeout: float = 10) -> dict[str, object] | None:
    try:
        def create_completion(*args: Any, **kwargs: Any) -> ChatCompletion:
            return _get_client().chat.completions.create(*args, **kwargs)

        # ``asyncio.to_thread`` runs the blocking OpenAI client in the event
        # loop's shared thread pool, so we reuse threads instead of spawning a
        # fresh ``ThreadPoolExecutor`` for every invocation.
        response = await asyncio.wait_for(
            asyncio.to_thread(
                create_completion,
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
    except asyncio.TimeoutError:
        logging.error("Command parsing timed out")
        return None
    except OpenAIError:
        logging.exception("Command parsing failed")
        return None
    except ValueError:
        logging.exception("Invalid value during command parsing")
        return None
    except TypeError:
        logging.exception("Invalid type during command parsing")
        return None
    except Exception:
        logging.exception("Unexpected error during command parsing")
        return None

    choices = getattr(response, "choices", None)
    if not choices:
        logging.error("No choices in GPT response")
        return None

    first = choices[0]
    message = getattr(first, "message", None)
    if message is None:
        logging.error("No message in first choice")
        return None

    content = getattr(message, "content", None)
    if content is None:
        logging.error("No content in GPT response")
        return None
    if not isinstance(content, str):
        logging.error("Content is not a string in GPT response")
        return None
    content = content.strip()
    if not content:
        logging.error("Content is empty in GPT response")
        return None

    safe_content = _sanitize_sensitive_data(content)
    logging.info("GPT raw response: %s", safe_content[:200])
    parsed = _extract_first_json(content)
    if parsed is None:
        logging.error("No JSON object found in response")
        return None
    try:
        return CommandSchema.model_validate(parsed).model_dump(exclude_none=True)
    except ValidationError:
        logging.exception("Invalid command structure")
        return None
