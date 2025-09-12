from __future__ import annotations

import asyncio
import datetime
import html
import io
import logging
from types import MappingProxyType
from typing import cast

from openai import OpenAIError
import httpx
from telegram import Message, Update
from telegram.constants import ChatAction, MessageLimit
from telegram.error import TelegramError
from telegram.ext import ContextTypes, ConversationHandler

from sqlalchemy.orm import Session

from services.api.app.diabetes.services.db import SessionLocal, User, run_db
from services.api.app.diabetes.services.gpt_client import (
    _get_client,
    create_thread_sync,
    send_message,
)
from services.api.app.diabetes.services.repository import CommitError, commit
from services.api.app.diabetes.utils.functions import extract_nutrition_info
from services.api.app.ui.keyboard import build_main_keyboard
from ..prompts import PHOTO_ANALYSIS_PROMPT

from . import EntryData, UserData

logger = logging.getLogger(__name__)

PHOTO_SUGAR = 7
WAITING_GPT_FLAG = "waiting_gpt_response"
WAITING_GPT_TIMESTAMP = "waiting_gpt_response_ts"
WAITING_GPT_TIMEOUT = datetime.timedelta(minutes=5)
RUN_RETRIEVE_TIMEOUT = 10  # seconds
END = ConversationHandler.END


def _clear_waiting_gpt(user_data: UserData) -> None:
    user_data.pop(WAITING_GPT_FLAG, None)
    user_data.pop(WAITING_GPT_TIMESTAMP, None)


def _get_mutable_user_data(context: ContextTypes.DEFAULT_TYPE) -> UserData:
    existing = getattr(context, "_user_data", None)
    if existing is not None:
        return cast(UserData, existing)
    raw = context.user_data
    if raw is None:
        data: UserData = {}
    elif isinstance(raw, MappingProxyType):
        data = dict(raw)
    else:
        data = cast(UserData, raw)
    context._user_data = data
    return data


async def _delete_status_message(
    status_message: Message | None, tag: str
) -> None:
    if not status_message or not hasattr(status_message, "delete"):
        return
    try:
        await status_message.delete()
    except TelegramError as exc:
        logger.warning(
            "[PHOTO][%s] Failed to delete status message: %s", tag, exc
        )
    except OSError as exc:
        logger.exception("[PHOTO][%s] OS error: %s", tag, exc)
        raise


async def photo_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt user to send a food photo for analysis."""
    message = update.message
    if message is None:
        return
    await message.reply_text(
        "📸 Пришлите фото блюда для анализа.", reply_markup=build_main_keyboard()
    )


async def photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_bytes: bytes | None = None,
) -> int:
    """Process food photos and trigger nutrition analysis."""
    user_data = _get_mutable_user_data(context)
    message = update.message
    if message is None:
        query = update.callback_query
        if query is None or query.message is None:
            return END
        message = query.message
    message = cast(Message, message)
    effective_user = update.effective_user
    if effective_user is None:
        return END
    user_id = effective_user.id

    flag_ts = user_data.get(WAITING_GPT_TIMESTAMP)
    now = datetime.datetime.now(datetime.timezone.utc)
    if user_data.get(WAITING_GPT_FLAG):
        if (
            isinstance(flag_ts, datetime.datetime)
            and now - flag_ts > WAITING_GPT_TIMEOUT
        ):
            _clear_waiting_gpt(user_data)
        else:
            await message.reply_text("⏳ Уже обрабатываю фото, подождите…")
            return END
    user_data[WAITING_GPT_FLAG] = True
    user_data[WAITING_GPT_TIMESTAMP] = now
    try:
        if file_bytes is None:
            try:
                photo = message.photo[-1]
            except (AttributeError, IndexError, TypeError):
                await message.reply_text("❗ Файл не распознан как изображение.")
                return END

            try:
                file = await context.bot.get_file(photo.file_id)
                file_bytes = bytes(await file.download_as_bytearray())
            except OSError as exc:
                logger.exception("[PHOTO] Failed to download photo: %s", exc)
                await message.reply_text("⚠️ Не удалось скачать фото. Попробуйте ещё раз.")
                return END
            except TelegramError as exc:
                logger.exception("[PHOTO] Failed to download photo: %s", exc)
                await message.reply_text("⚠️ Не удалось скачать фото. Попробуйте ещё раз.")
                return END

        logger.info("[PHOTO] Received photo from user %s", user_id)

        thread_id = user_data.get("thread_id")
        if not thread_id:

            def _fetch_or_create(session: Session) -> str:
                user = session.get(User, user_id)
                if user:
                    return user.thread_id
                thread_id_local = create_thread_sync()
                session.add(User(telegram_id=user_id, thread_id=thread_id_local))
                commit(session)
                return thread_id_local

            try:
                thread_id = await run_db(_fetch_or_create, sessionmaker=SessionLocal)
            except CommitError:
                logger.exception("[PHOTO] Failed to commit user %s", user_id)
                await message.reply_text("⚠️ Не удалось сохранить данные пользователя.")
                return END
            user_data["thread_id"] = thread_id

        try:
            run = await send_message(
                thread_id=thread_id,
                content=PHOTO_ANALYSIS_PROMPT,
                image_bytes=file_bytes,
            )
        except asyncio.TimeoutError:
            logger.warning("[PHOTO] GPT request timed out")
            await message.reply_text(
                "⚠️ Превышено время ожидания ответа. Попробуйте ещё раз."
            )
            return END
        status_message = await message.reply_text(
            "🔍 Анализирую фото (это займёт 5‑10 с)…"
        )
        chat_id = getattr(message, "chat_id", None)

        async def send_typing_action() -> None:
            if not chat_id:
                return
            try:
                await context.bot.send_chat_action(
                    chat_id=chat_id, action=ChatAction.TYPING
                )
            except TelegramError as exc:
                logger.warning(
                    "[PHOTO][TYPING_ACTION] Failed to send typing action: %s",
                    exc,
                )
            except OSError as exc:
                logger.exception(
                    "[PHOTO][TYPING_ACTION] OS error: %s",
                    exc,
                )
                raise

        await send_typing_action()

        max_attempts = 15
        warn_after = 5
        for attempt in range(max_attempts):
            if run.status in ("completed", "failed", "cancelled", "expired"):
                break
            await asyncio.sleep(2)
            try:
                run = await asyncio.wait_for(
                    asyncio.to_thread(
                        _get_client().beta.threads.runs.retrieve,
                        thread_id=run.thread_id,
                        run_id=run.id,
                    ),
                    timeout=RUN_RETRIEVE_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.warning("[PHOTO][RUN_RETRIEVE] Timed out retrieving run")
                await _delete_status_message(status_message, "RUN_RETRIEVE_DELETE")
                await message.reply_text(
                    "⚠️ Превышено время ожидания Vision. Попробуйте ещё раз."
                )
                return END
            except (OpenAIError, httpx.HTTPError) as exc:
                logger.exception(
                    "[PHOTO][RUN_RETRIEVE] Failed to retrieve run: %s", exc
                )
                await _delete_status_message(status_message, "RUN_RETRIEVE_DELETE")
                await message.reply_text(
                    "⚠️ Vision не смог обработать фото. Попробуйте ещё раз."
                )
                return END
            if attempt == warn_after:
                await send_typing_action()
        else:
            await _delete_status_message(status_message, "TIMEOUT_DELETE")
            await message.reply_text(
                "⚠️ Время ожидания Vision истекло. Попробуйте позже."
            )
            return END

        if run.status != "completed":
            logger.error("[VISION][RUN_FAILED] run.status=%s", run.status)
            if status_message and hasattr(status_message, "edit_text"):
                try:
                    await status_message.edit_text(
                        "⚠️ Vision не смог обработать фото. Попробуйте ещё раз."
                    )
                except TelegramError as exc:
                    logger.warning(
                        "[PHOTO][RUN_FAILED_EDIT] Failed to send Vision failure notice: %s",
                        exc,
                    )
                except OSError as exc:
                    logger.exception(
                        "[PHOTO][RUN_FAILED_EDIT] OS error: %s",
                        exc,
                    )
                    raise
            else:
                await message.reply_text(
                    "⚠️ Vision не смог обработать фото. Попробуйте ещё раз."
                )
            return END

        try:
            messages = await asyncio.to_thread(
                _get_client().beta.threads.messages.list,
                thread_id=run.thread_id,
                run_id=run.id,
            )
        except TypeError:
            messages = await asyncio.to_thread(
                _get_client().beta.threads.messages.list,
                thread_id=run.thread_id,
            )
        vision_text = ""
        for m in messages.data:
            if getattr(m, "run_id", run.id) != run.id:
                continue
            if m.role == "assistant" and m.content:
                first_block: object = m.content[0]
                text_block = getattr(first_block, "text", None)
                if text_block is not None:
                    vision_text = text_block.value
                    break
        logger.debug(
            "[VISION][RESPONSE] Ответ Vision для пользователя %s:\n%s",
            user_id,
            vision_text,
        )

        nutrition = extract_nutrition_info(vision_text)
        if nutrition.carbs_g is None and nutrition.xe is None:
            logger.debug(
                "[VISION][NO_PARSE] Ответ ассистента: %r для пользователя: %s",
                vision_text,
                user_id,
            )
            text = (
                "⚠️ Не смог разобрать углеводы на фото.\n\n"
                f"Вот полный ответ Vision:\n<pre>{html.escape(vision_text)}</pre>\n"
                "Введите /dose и укажите их вручную."
            )
            parse_mode: str | None = "HTML"
            if len(text) > MessageLimit.MAX_TEXT_LENGTH:
                await message.reply_document(
                    document=io.BytesIO(vision_text.encode("utf-8")),
                    filename="vision.txt",
                )
                text = (
                    "⚠️ Не смог разобрать углеводы на фото.\n\n"
                    "⚠️ Ответ Vision слишком длинный, полный текст во вложении.\n"
                    "Введите /dose и укажите их вручную."
                )
                parse_mode = None
            await message.reply_text(
                text,
                parse_mode=parse_mode,
                reply_markup=build_main_keyboard(),
            )
            user_data.pop("pending_entry", None)
            return END

        pending_entry = cast(
            EntryData,
            user_data.get("pending_entry")
            or {
                "telegram_id": user_id,
                "event_time": datetime.datetime.now(datetime.timezone.utc),
            },
        )
        pending_entry.update(
            {
                "carbs_g": nutrition.carbs_g,
                "xe": nutrition.xe,
                "weight_g": nutrition.weight_g,
                "protein_g": nutrition.protein_g,
                "fat_g": nutrition.fat_g,
                "calories_kcal": nutrition.calories_kcal,
                "photo_path": None,
            }
        )
        user_data["pending_entry"] = pending_entry
        await _delete_status_message(status_message, "DELETE_STATUS")
        prefix = "🍽️ На фото:\n"
        suffix = "Введите текущий сахар (ммоль/л) — и я рассчитаю дозу инсулина."
        text = f"{prefix}{vision_text}\n\n{suffix}"
        if len(text) > MessageLimit.MAX_TEXT_LENGTH:
            notice = "⚠️ Ответ Vision слишком длинный, полный текст во вложении."
            max_len = max(
                0,
                MessageLimit.MAX_TEXT_LENGTH
                - len(prefix)
                - len("\n\n")
                - len(notice)
                - len("\n\n")
                - len(suffix)
                - 3,
            )
            truncated = vision_text[:max_len] + "..."
            await message.reply_document(
                document=io.BytesIO(vision_text.encode("utf-8")),
                filename="vision.txt",
            )
            text = f"{prefix}{truncated}\n\n{notice}\n\n{suffix}"
        await message.reply_text(text, reply_markup=build_main_keyboard())
        return PHOTO_SUGAR

    except OSError as exc:
        logger.exception("[PHOTO] File processing error: %s", exc)
        await message.reply_text(
            "⚠️ Ошибка при обработке файла изображения. Попробуйте ещё раз."
        )
        return END
    except OpenAIError as exc:
        logger.exception("[PHOTO] Vision API error: %s", exc)
        await message.reply_text(
            "⚠️ Vision не смог обработать фото. Попробуйте ещё раз."
        )
        return END
    except ValueError as exc:
        logger.exception("[PHOTO] Parsing error: %s", exc)
        await message.reply_text("⚠️ Не удалось распознать фото. Попробуйте ещё раз.")
        return END
    except TelegramError as exc:
        logger.exception("[PHOTO] Telegram error: %s", exc)
        await message.reply_text("⚠️ Произошла ошибка Telegram. Попробуйте ещё раз.")
        return END
    finally:
        _clear_waiting_gpt(user_data)


async def doc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle images sent as documents."""
    if getattr(context, "user_data", None) is None:
        return END
    _get_mutable_user_data(context)
    message = update.message
    if message is None:
        return END
    effective_user = update.effective_user
    if effective_user is None:
        return END

    document = message.document
    if document is None:
        return END

    mime_type = document.mime_type
    if mime_type is None or not mime_type.startswith("image/"):
        return END

    try:
        file = await context.bot.get_file(document.file_id)
        file_bytes = bytes(await file.download_as_bytearray())
    except OSError as exc:
        logger.exception("[DOC] Failed to download document: %s", exc)
        await message.reply_text("⚠️ Не удалось сохранить документ. Попробуйте ещё раз.")
        return END
    except TelegramError as exc:
        logger.exception("[DOC] Failed to download document: %s", exc)
        await message.reply_text("⚠️ Не удалось сохранить документ. Попробуйте ещё раз.")
        return END

    return await photo_handler(update, context, file_bytes=file_bytes)


prompt_photo = photo_prompt

__all__ = [
    "PHOTO_SUGAR",
    "WAITING_GPT_FLAG",
    "WAITING_GPT_TIMESTAMP",
    "WAITING_GPT_TIMEOUT",
    "photo_prompt",
    "photo_handler",
    "doc_handler",
    "prompt_photo",
]
