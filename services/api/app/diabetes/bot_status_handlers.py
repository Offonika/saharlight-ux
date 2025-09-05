from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.parse
from typing import Any, TypeAlias

import aiohttp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import CommandHandler, ContextTypes

from ..telegram_auth import TG_INIT_DATA_HEADER


CommandHandlerT: TypeAlias = CommandHandler[ContextTypes.DEFAULT_TYPE, object]


def _build_init_data(user_id: int, token: str) -> str:
    """Return WebApp init data for ``user_id`` signed with ``token``."""

    user = json.dumps({"id": user_id}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "query_id": "status", "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


def build_status_handler(ui_base_url: str, api_base: str = "/api") -> CommandHandlerT:
    """Return a /status handler that shows onboarding progress."""

    async def _status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return

        token = os.environ.get("TELEGRAM_TOKEN")
        if not token:
            await update.message.reply_text("Server misconfigured")
            return

        user_id = update.effective_user.id
        init_data = _build_init_data(user_id, token)
        url = f"{api_base.rstrip('/')}/onboarding/status"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers={TG_INIT_DATA_HEADER: init_data}
                ) as resp:
                    data: dict[str, Any] = await resp.json()
        except Exception:
            await update.message.reply_text("Не удалось получить статус онбординга")
            return

        completed = bool(data.get("completed"))
        missing = [str(s) for s in data.get("missing", [])]

        profile_url = f"{ui_base_url.rstrip('/')}/profile?flow=onboarding&step=profile"
        reminders_url = (
            f"{ui_base_url.rstrip('/')}/reminders?flow=onboarding&step=reminders"
        )

        if not completed:
            btns: list[list[InlineKeyboardButton]] = []
            if "profile" in missing:
                btns.append(
                    [
                        InlineKeyboardButton(
                            "🧾 Открыть профиль",
                            web_app=WebAppInfo(url=profile_url),
                        )
                    ]
                )
            if "reminders" in missing:
                btns.append(
                    [
                        InlineKeyboardButton(
                            "⏰ Открыть напоминания",
                            web_app=WebAppInfo(url=reminders_url),
                        )
                    ]
                )
            await update.message.reply_text(
                "Ещё пара шагов — продолжим настройку:",
                reply_markup=InlineKeyboardMarkup(btns),
            )
        else:
            btns = [
                [
                    InlineKeyboardButton(
                        "🧾 Открыть профиль", web_app=WebAppInfo(url=profile_url)
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⏰ Открыть напоминания",
                        web_app=WebAppInfo(url=reminders_url),
                    )
                ],
            ]
            await update.message.reply_text(
                "✅ Онбординг завершён. Чем помочь дальше?",
                reply_markup=InlineKeyboardMarkup(btns),
            )

    return CommandHandlerT("status", _status)
