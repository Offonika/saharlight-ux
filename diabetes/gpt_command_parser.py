import asyncio
import logging
import json
import re

from openai import OpenAIError

from diabetes.gpt_client import _get_client

# gpt_command_parser.py  ← замените весь блок SYSTEM_PROMPT
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


def _extract_first_json(text: str) -> dict | None:
    """Return the first JSON object found in *text* or ``None`` if absent."""
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(text):
        match = re.search(r"[\[{]", text[idx:])
        if not match:
            return None
        start = idx + match.start()
        try:
            obj, end = decoder.raw_decode(text, start)
            if isinstance(obj, dict):
                return obj
            idx = end
        except json.JSONDecodeError:
            idx = start + 1
    return None


async def parse_command(text: str, timeout: float = 10) -> dict | None:
    try:
        # ``asyncio.to_thread`` reuses the loop's default thread pool, avoiding
        # the overhead of creating a new ``ThreadPoolExecutor`` on each call.
        response = await asyncio.wait_for(
            asyncio.to_thread(
                _get_client().chat.completions.create,
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
    except Exception:
        logging.exception("Unexpected error during command parsing")
        return None

    choices = getattr(response, "choices", None)
    if not choices:
        logging.error("No choices in GPT response")
        return None
    content = choices[0].message.content.strip()
    safe_content = _sanitize_sensitive_data(content)
    logging.info("GPT raw response: %s", safe_content[:200])
    parsed = _extract_first_json(content)
    if parsed is None:
        logging.error("No JSON object found in response")
        return None
    return parsed
