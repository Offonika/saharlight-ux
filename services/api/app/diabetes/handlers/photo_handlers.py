from __future__ import annotations

import asyncio
import datetime
import html
import logging
import os
import tempfile
from pathlib import Path
from typing import cast

from openai import OpenAIError
from telegram import Message, Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import ContextTypes, ConversationHandler

from services.api.app.diabetes.services.db import SessionLocal, User
from services.api.app.diabetes.services.gpt_client import (
    _get_client,
    create_thread,
    send_message,
)
from services.api.app.diabetes.services.repository import CommitError, commit
from services.api.app.diabetes.utils.functions import extract_nutrition_info
from services.api.app.diabetes.utils.ui import menu_keyboard

from . import EntryData, UserData

logger = logging.getLogger(__name__)

PHOTO_SUGAR = 7
WAITING_GPT_FLAG = "waiting_gpt_response"
WAITING_GPT_TIMESTAMP = "waiting_gpt_response_ts"
WAITING_GPT_TIMEOUT = datetime.timedelta(minutes=5)
END = ConversationHandler.END


def _clear_waiting_gpt(user_data: UserData) -> None:
    user_data.pop(WAITING_GPT_FLAG, None)
    user_data.pop(WAITING_GPT_TIMESTAMP, None)


async def photo_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt user to send a food photo for analysis."""
    message = update.message
    if message is None:
        return
    await message.reply_text(
        "📸 Пришлите фото блюда для анализа.", reply_markup=menu_keyboard()
    )


async def photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_path: str | None = None,
) -> int:
    """Process food photos and trigger nutrition analysis."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        return END
    user_data = cast(UserData, user_data_raw)
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

    if file_path is None:
        file_path = user_data.pop("__file_path", None)

    if not file_path:
        try:
            photo = message.photo[-1]
        except (AttributeError, IndexError, TypeError):
            await message.reply_text("❗ Файл не распознан как изображение.")
            _clear_waiting_gpt(user_data)
            return END

        photos_dir = os.path.join(
            tempfile.gettempdir(), "diabetes-bot-photos"
        )
        try:
            os.makedirs(photos_dir, exist_ok=True)
            file_path = f"{photos_dir}/{user_id}_{photo.file_unique_id}.jpg"
            file = await context.bot.get_file(photo.file_id)
            await file.download_to_drive(file_path)
        except OSError as exc:
            logger.exception("[PHOTO] Failed to save photo: %s", exc)
            await message.reply_text("⚠️ Не удалось сохранить фото. Попробуйте ещё раз.")
            _clear_waiting_gpt(user_data)
            return END
        except TelegramError as exc:
            logger.exception("[PHOTO] Failed to save photo: %s", exc)
            await message.reply_text("⚠️ Не удалось сохранить фото. Попробуйте ещё раз.")
            _clear_waiting_gpt(user_data)
            return END

    logger.info("[PHOTO] Saved to %s", file_path)

    try:
        thread_id = user_data.get("thread_id")
        if not thread_id:
            with SessionLocal() as session:
                user = session.get(User, user_id)
                if user:
                    thread_id = user.thread_id
                else:
                    thread_id = await create_thread()
                    session.add(User(telegram_id=user_id, thread_id=thread_id))
                    try:
                        commit(session)
                    except CommitError:
                        await message.reply_text(
                            "⚠️ Не удалось сохранить данные пользователя."
                        )
                        return END
            user_data["thread_id"] = thread_id

        try:
            run = await send_message(
                thread_id=thread_id,
                content=(
                    "Определи **название** блюда и количество углеводов/ХЕ. Ответ:\n"
                    "<название блюда>\n"
                    "Углеводы: <...>\n"
                    "ХЕ: <...>"
                ),
                image_path=file_path,
                keep_image=True,
            )
        except asyncio.TimeoutError:
            logger.warning("[PHOTO] GPT request timed out")
            await message.reply_text(
                "⚠️ Превышено время ожидания ответа. Попробуйте ещё раз."
            )
            _clear_waiting_gpt(user_data)
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
            run = await asyncio.to_thread(
                _get_client().beta.threads.runs.retrieve,
                thread_id=run.thread_id,
                run_id=run.id,
            )
            if attempt == warn_after:
                await send_typing_action()
        else:
            if status_message and hasattr(status_message, "delete"):
                try:
                    await status_message.delete()
                except TelegramError as exc:
                    logger.warning(
                        "[PHOTO][TIMEOUT_DELETE] Failed to delete status message: %s",
                        exc,
                    )
                except OSError as exc:
                    logger.exception(
                        "[PHOTO][TIMEOUT_DELETE] OS error: %s",
                        exc,
                    )
                    raise
            await message.reply_text(
                "⚠️ Время ожидания Vision истекло. Попробуйте позже."
            )
            return END

        if run.status != "completed":
            logger.error("[VISION][RUN_FAILED] run.status=%s", run.status)
            if status_message and hasattr(status_message, "edit_text"):
                try:
                    await status_message.edit_text("⚠️ Vision не смог обработать фото.")
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
                await message.reply_text("⚠️ Vision не смог обработать фото.")
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
            "[VISION][RESPONSE] Ответ Vision для %s:\n%s",
            file_path,
            vision_text,
        )

        carbs_g, xe = extract_nutrition_info(vision_text)
        if carbs_g is None and xe is None:
            logger.debug(
                "[VISION][NO_PARSE] Ответ ассистента: %r для файла: %s",
                vision_text,
                file_path,
            )
            await message.reply_text(
                "⚠️ Не смог разобрать углеводы на фото.\n\n"
                f"Вот полный ответ Vision:\n<pre>{html.escape(vision_text)}</pre>\n"
                "Введите /dose и укажите их вручную.",
                parse_mode="HTML",
                reply_markup=menu_keyboard(),
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
        pending_entry.update({"carbs_g": carbs_g, "xe": xe, "photo_path": file_path})
        user_data["pending_entry"] = pending_entry
        if status_message and hasattr(status_message, "delete"):
            try:
                await status_message.delete()
            except TelegramError as exc:
                logger.warning(
                    "[PHOTO][DELETE_STATUS] Failed to delete status message: %s",
                    exc,
                )
            except OSError as exc:
                logger.exception(
                    "[PHOTO][DELETE_STATUS] OS error: %s",
                    exc,
                )
                raise
        await message.reply_text(
            f"🍽️ На фото:\n{vision_text}\n\nВведите текущий сахар (ммоль/л) — и я рассчитаю дозу инсулина.",
            reply_markup=menu_keyboard(),
        )
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
        if file_path:
            try:
                Path(file_path).unlink()
            except OSError as exc:
                logger.warning(
                    "[PHOTO][CLEANUP] Failed to remove file %s: %s",
                    file_path,
                    exc,
                )


async def doc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle images sent as documents."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        return END
    user_data = cast(UserData, user_data_raw)
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

    user_id = effective_user.id
    filename = document.file_name or ""
    ext = Path(filename).suffix or ".jpg"
    photos_dir = os.path.join(tempfile.gettempdir(), "diabetes-bot-photos")
    path = f"{photos_dir}/{user_id}_{document.file_unique_id}{ext}"
    try:
        os.makedirs(photos_dir, exist_ok=True)
        file = await context.bot.get_file(document.file_id)
        await file.download_to_drive(path)
    except OSError as exc:
        logger.exception("[DOC] Failed to save document: %s", exc)
        await message.reply_text("⚠️ Не удалось сохранить документ. Попробуйте ещё раз.")
        return END
    except TelegramError as exc:
        logger.exception("[DOC] Failed to save document: %s", exc)
        await message.reply_text("⚠️ Не удалось сохранить документ. Попробуйте ещё раз.")
        return END

    user_data.pop("__file_path", None)
    return await photo_handler(update, context, file_path=path)


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
