from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from typing import Iterable, MutableMapping, cast

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from telegram import Message, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes, ConversationHandler

from services.api.app.ui.keyboard import build_main_keyboard

logger = logging.getLogger(__name__)


# Keys and values for tracking the kind of input the user sent.
AWAITING_KIND = "labs_awaiting_kind"
KIND_FILE = "file"
KIND_TEXT = "text"

END = ConversationHandler.END


# Typical reference ranges used when none are provided by the user.
DEFAULT_REFS: dict[str, tuple[float, float]] = {
    "глюкоза": (3.3, 5.5),
    "hba1c": (4.0, 6.0),
    "лейкоциты": (4.0, 9.0),
    "alt": (10.0, 40.0),
}


# Simple patterns to skip medication prescriptions or dosages.
MEDICATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bмг\b", re.IGNORECASE),
    re.compile(r"\bmg\b", re.IGNORECASE),
    re.compile(r"\bед\.?\b", re.IGNORECASE),
    re.compile(r"\bтаб\.?\b", re.IGNORECASE),
)


@dataclass
class LabResult:
    """Structured representation of a parsed lab value."""

    name: str
    value: float
    ref_low: float | None
    ref_high: float | None


def _parse_line(line: str) -> LabResult | None:
    """Parse a single line of lab result text."""

    if any(p.search(line) for p in MEDICATION_PATTERNS):
        return None
    m = re.search(r"^([^:]+?):\s*([\d.,]+)", line)
    if not m:
        return None
    name = m.group(1).strip()
    value_str = m.group(2).replace(",", ".")
    try:
        value = float(value_str)
    except ValueError:
        logger.warning(
            "Skipping lab line due to invalid value '%s': %s", value_str, line
        )
        return None
    ref_low: float | None = None
    ref_high: float | None = None
    m_ref = re.search(r"([\d.,]+)\s*[–-]\s*([\d.,]+)", line)
    if m_ref:
        ref_low_str = m_ref.group(1).replace(",", ".")
        ref_high_str = m_ref.group(2).replace(",", ".")
        try:
            ref_low = float(ref_low_str)
            ref_high = float(ref_high_str)
        except ValueError:
            logger.warning(
                "Skipping lab line due to invalid reference range '%s'-'%s': %s",
                ref_low_str,
                ref_high_str,
                line,
            )
            return None
    else:
        default = DEFAULT_REFS.get(name.lower())
        if default:
            ref_low, ref_high = default
    return LabResult(name, value, ref_low, ref_high)


def parse_labs(text: str) -> list[LabResult]:
    """Extract lab results from raw ``text``."""

    results: list[LabResult] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = _parse_line(line)
        if parsed:
            results.append(parsed)
    return results


def classify(result: LabResult) -> str:
    """Classify result into normal/borderline/alarming."""

    if result.ref_low is None or result.ref_high is None:
        return "borderline"
    if result.ref_low <= result.value <= result.ref_high:
        return "norm"
    span = result.ref_high - result.ref_low
    if result.value < result.ref_low:
        diff = result.ref_low - result.value
    else:
        diff = result.value - result.ref_high
    if span and diff > 0.2 * span:
        return "alarm"
    return "borderline"


def format_reply(results: Iterable[LabResult]) -> str:
    """Format parsed ``results`` into a multi-section reply."""

    sections: dict[str, list[str]] = {
        "norm": [],
        "borderline": [],
        "alarm": [],
    }
    discuss: list[str] = []
    for res in results:
        category = classify(res)
        entry = f"{res.name}: {res.value}"
        if res.ref_low is not None and res.ref_high is not None:
            entry += f" (норма {res.ref_low}-{res.ref_high})"
        sections[category].append(entry)
        if category != "norm":
            discuss.append(res.name)

    parts: list[str] = []
    if sections["norm"]:
        parts.append("*норма:*\n- " + "\n- ".join(sections["norm"]))
    if sections["borderline"]:
        parts.append("*погранично:*\n- " + "\n- ".join(sections["borderline"]))
    if sections["alarm"]:
        parts.append("*тревожно:*\n- " + "\n- ".join(sections["alarm"]))
    if discuss:
        parts.append("*что обсудить с врачом:*\n- " + "\n- ".join(discuss))
    return "\n\n".join(parts) if parts else "Не удалось распознать анализы."


def _extract_text_from_file(file_bytes: bytes, mime: str | None) -> str:
    """Extract text from ``file_bytes`` using simple heuristics."""

    if mime and "pdf" in mime.lower():
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except (PdfReadError, OSError) as exc:  # pragma: no cover - best effort
            logger.warning("Failed to read PDF: %s", exc)
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return ""


async def _download_file(message: Message, ctx: ContextTypes.DEFAULT_TYPE) -> tuple[bytes, str | None] | None:
    """Download a document or photo and return its bytes and MIME type."""

    document = message.document
    if document is not None:
        try:
            file = await ctx.bot.get_file(document.file_id)
            data = bytes(await file.download_as_bytearray())
            return data, document.mime_type
        except (TelegramError, OSError) as exc:  # pragma: no cover - network errors
            logger.exception("Failed to download document: %s", exc)
            return None

    photo = message.photo
    if photo:
        try:
            file = await ctx.bot.get_file(photo[-1].file_id)
            data = bytes(await file.download_as_bytearray())
            return data, "image/jpeg"
        except (TelegramError, OSError) as exc:  # pragma: no cover - network errors
            logger.exception("Failed to download photo: %s", exc)
            return None
    return None


async def labs_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """Process lab results sent as text, photo or document."""

    message = update.effective_message
    if message is None:
        return END

    user_data = cast(MutableMapping[str, object], ctx.user_data or {})
    if not user_data.get("waiting_labs") and user_data.get("assistant_last_mode") != "labs":
        return END

    kind = KIND_TEXT
    text = message.text or ""
    if not text:
        downloaded = await _download_file(message, ctx)
        if downloaded is None:
            await message.reply_text("⚠️ Не удалось получить файл.")
            user_data.pop("waiting_labs", None)
            user_data.pop("assistant_last_mode", None)
            return END
        file_bytes, mime = downloaded
        if mime and not (mime.lower().startswith(("image/", "text/")) or "pdf" in mime.lower()):
            logger.warning("Unsupported MIME type: %s", mime)
            await message.reply_text("⚠️ Неподдерживаемый тип файла.")
            user_data.pop("waiting_labs", None)
            user_data.pop("assistant_last_mode", None)
            return END
        kind = KIND_FILE
        text = _extract_text_from_file(file_bytes, mime)

    user_data[AWAITING_KIND] = kind
    results = parse_labs(text)
    reply = format_reply(results)
    await message.reply_text(
        reply,
        reply_markup=build_main_keyboard(),
        disable_web_page_preview=True,
    )
    user_data.pop("waiting_labs", None)
    user_data.pop("assistant_last_mode", None)
    return END


__all__ = [
    "AWAITING_KIND",
    "KIND_FILE",
    "KIND_TEXT",
    "END",
    "parse_labs",
    "labs_handler",
    "format_reply",
]
