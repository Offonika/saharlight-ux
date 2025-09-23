"""Handlers for preparing doctor visit checklists and notes."""

from __future__ import annotations

import logging
from typing import cast

from fastapi import HTTPException
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from services.api.app.assistant.services import memory_service
from services.api.app.services import profile as profile_service

logger = logging.getLogger(__name__)

__all__ = ["send_checklist", "save_note_callback"]


async def send_checklist(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Collect user profile and send visit checklist."""

    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return
    try:
        profile = await profile_service.get_profile(user.id)
    except HTTPException as exc:
        if exc.status_code == 404:
            await message.reply_text(
                "Заполните, пожалуйста, профиль, чтобы мы могли подготовить чек-лист."
            )
            return
        logger.exception("Failed to fetch profile for user %s", user.id)
        raise
    await memory_service.get_memory(user.id)  # placeholder usage
    questions = [
        "Как вы себя чувствуете?",
        "Какой у вас был последний сахар?",
        f"Целевая гликемия: {profile.target_bg if profile.target_bg is not None else 'не задана'}",
    ]
    text = "Чек-лист визита:\n" + "\n".join(f"- {q}" for q in questions)
    user_data = cast(dict[str, object], ctx.user_data)
    user_data["visit_note"] = text
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Сохранить заметку", callback_data="asst:save_note")]]
    )
    await message.reply_text(text, reply_markup=keyboard)


async def save_note_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Persist generated note via memory service."""

    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return
    await query.answer()
    user_data = cast(dict[str, object], ctx.user_data)
    note = cast(str | None, user_data.get("visit_note"))
    if not note:
        await query.edit_message_text("❗ Нет заметки для сохранения.")
        return
    await memory_service.save_note(user.id, note)
    user_data.pop("visit_note", None)
    await query.edit_message_text("✅ Заметка сохранена.")
