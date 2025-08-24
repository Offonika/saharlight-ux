"""Handlers related to patient profile management."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
import json
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy.orm import Session

from services.api.app.diabetes.services.db import (
    SessionLocal,
    Profile,
    Alert,
    Reminder,
    User,
)
from services.api.app.diabetes.utils.ui import BACK_BUTTON_TEXT, PHOTO_BUTTON_TEXT

logger = logging.getLogger(__name__)

run_db: Callable[..., Awaitable[object]] | None
try:
    from services.api.app.diabetes.services.db import run_db as _run_db
except ImportError:  # pragma: no cover - optional db runner
    run_db = None
except Exception as exc:  # pragma: no cover - log unexpected errors
    logger.exception("Unexpected error importing run_db", exc_info=exc)
    raise
else:
    run_db = cast(Callable[..., Awaitable[object]], _run_db)

from services.api.app.diabetes.handlers.alert_handlers import (  # noqa: E402
    evaluate_sugar,
    DefaultJobQueue,
)
from services.api.app.diabetes.handlers.callbackquery_no_warn_handler import (  # noqa: E402
    CallbackQueryNoWarnHandler,
)
from services.api.app.diabetes.utils.ui import (  # noqa: E402
    build_timezone_webapp_button,
    back_keyboard as _back_keyboard,
    menu_keyboard,
)
from services.api.app import config  # noqa: E402
from services.api.app.diabetes.services.repository import CommitError, commit  # noqa: E402
import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers  # noqa: E402

from .api import (  # noqa: E402
    get_api,
    save_profile,
    set_timezone,
    fetch_profile,
    post_profile,
)
from .validation import parse_profile_args  # noqa: E402

back_keyboard: ReplyKeyboardMarkup = _back_keyboard

from .. import UserData  # noqa: E402


MSG_ICR_GT0 = "ИКХ должен быть больше 0."
MSG_CF_GT0 = "КЧ должен быть больше 0."
MSG_TARGET_GT0 = "Целевой сахар должен быть больше 0."
MSG_LOW_GT0 = "Нижний порог должен быть больше 0."
MSG_HIGH_GT_LOW = "Верхний порог должен быть больше нижнего и больше 0."


PROFILE_ICR, PROFILE_CF, PROFILE_TARGET, PROFILE_LOW, PROFILE_HIGH, PROFILE_TZ = range(6)
END: int = ConversationHandler.END


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle ``/profile`` command.

    * ``/profile`` → start step-by-step profile setup (conversation)
    * ``/profile help`` → show usage instructions
    * ``/profile <args>`` → set profile directly
    """

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return END

    args = context.args or []
    api, ApiException, ProfileModel = get_api()

    # Ensure no pending sugar logging conversation captures profile input
    from ..dose_calc import sugar_conv

    chat_data = getattr(context, "chat_data", {})
    if chat_data.pop("sugar_active", None):
        end_conv = getattr(sugar_conv, "update_state", None)
        if callable(end_conv):
            end_conv(update, context, END)
        else:
            chat_id = getattr(update.effective_chat, "id", None) if sugar_conv.per_chat else None
            user_id = getattr(update.effective_user, "id", None) if sugar_conv.per_user else None
            msg_id = getattr(update.effective_message, "message_id", None) if sugar_conv.per_message else None
            key = cast(
                tuple[int | str, ...],
                tuple(i for i in (chat_id, user_id, msg_id) if i is not None),
            )
            if hasattr(sugar_conv, "_update_state"):
                sugar_conv._update_state(END, key)
            else:
                logger.warning("sugar_conv lacks _update_state method")

    help_text = (
        "❗ Формат команды:\n"
        "/profile <ИКХ г/ед.> <КЧ ммоль/л> <целевой ммоль/л> <низкий ммоль/л> <высокий ммоль/л>\n"
        "или /profile icr=<ИКХ> cf=<КЧ> target=<целевой> low=<низкий> high=<высокий>\n"
        "Пример: /profile 10 2 6 4 9 — ИКХ 10 г/ед., КЧ 2 ммоль/л, целевой 6 ммоль/л, низкий 4 ммоль/л, высокий 9 ммоль/л"
    )

    if len(args) == 1 and args[0].lower() == "help":
        await message.reply_text(help_text, parse_mode="Markdown")
        return END

    if not args:
        await message.reply_text(
            "Введите коэффициент ИКХ (г/ед.) — сколько граммов углеводов покрывает 1 ед. быстрого инсулина:",
            reply_markup=back_keyboard,
        )
        return PROFILE_ICR

    values = parse_profile_args(args)
    if values is None:
        await message.reply_text("❗ Неверный формат. Справка: /profile help")
        return END

    try:
        icr = float(values["icr"].replace(",", "."))
        cf = float(values["cf"].replace(",", "."))
        target = float(values["target"].replace(",", "."))
        low = float(values["low"].replace(",", "."))
        high = float(values["high"].replace(",", "."))
    except ValueError:
        await message.reply_text("❗ Пожалуйста, введите корректные числа. Справка: /profile help")
        return END

    if icr <= 0:
        await message.reply_text(MSG_ICR_GT0)
        return END
    if cf <= 0:
        await message.reply_text(MSG_CF_GT0)
        return END
    if target <= 0:
        await message.reply_text(MSG_TARGET_GT0)
        return END
    if low <= 0:
        await message.reply_text(MSG_LOW_GT0)
        return END
    if high <= low:
        await message.reply_text(MSG_HIGH_GT_LOW)
        return END

    warning_msg = ""
    if icr > 8 or cf < 3:
        warning_msg = (
            "\n⚠️ Проверьте, пожалуйста: возможно, вы перепутали местами ИКХ и КЧ.\n"
            f"• Вы ввели ИКХ = {icr} г/ед. (высоковато)\n"
            f"• КЧ = {cf} ммоль/л (низковато)\n\n"
            "Если вы хотели ввести наоборот, отправьте:\n"
            f"/profile {cf} {icr} {target} {low} {high}\n"
            f"(ИКХ {cf}, КЧ {icr}, целевой {target}, низкий {low}, высокий {high})\n"
        )

    user_id = user.id
    ok, err = post_profile(
        api,
        ApiException,
        ProfileModel,
        user_id,
        icr,
        cf,
        target,
        low,
        high,
    )
    if not ok:
        await message.reply_text(err or "⚠️ Не удалось сохранить профиль.")
        return END

    await message.reply_text(
        f"✅ Профиль обновлён:\n"
        f"• ИКХ: {icr} г/ед.\n"
        f"• КЧ: {cf} ммоль/л\n"
        f"• Целевой сахар: {target} ммоль/л\n"
        f"• Низкий порог: {low} ммоль/л\n"
        f"• Высокий порог: {high} ммоль/л" + warning_msg,
        parse_mode="Markdown",
        reply_markup=menu_keyboard(),
    )
    return END


async def profile_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display current patient profile."""
    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    api, ApiException, _ = get_api()
    user_id = user.id
    profile = fetch_profile(api, ApiException, user_id)

    if not profile:
        if config.get_webapp_url():
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📝 Заполнить форму",
                            web_app=WebAppInfo(reminder_handlers.build_webapp_url("/profile")),
                        )
                    ]
                ]
            )
            await message.reply_text("Ваш профиль пока не настроен.", reply_markup=keyboard)
        else:
            await message.reply_text(
                "Ваш профиль пока не настроен.\n\n"
                "Чтобы настроить профиль, введите команду:\n"
                "/profile <ИКХ г/ед.> <КЧ ммоль/л> <целевой ммоль/л> <низкий ммоль/л> <высокий ммоль/л>\n"
                "или /profile icr=<ИКХ> cf=<КЧ> target=<целевой> low=<низкий> high=<высокий>\n"
                "Пример: /profile 10 2 6 4 9 — ИКХ 10 г/ед., КЧ 2 ммоль/л, целевой 6 ммоль/л, низкий 4 ммоль/л, высокий 9 ммоль/л",
                parse_mode="Markdown",
            )
        return

    msg = (
        "📄 Ваш профиль:\n"
        f"• ИКХ: {profile.icr} г/ед.\n"
        f"• КЧ: {profile.cf} ммоль/л\n"
        f"• Целевой сахар: {profile.target} ммоль/л\n"
        f"• Низкий порог: {profile.low} ммоль/л\n"
        f"• Высокий порог: {profile.high} ммоль/л"
    )
    rows = [
        [InlineKeyboardButton("✏️ Изменить", callback_data="profile_edit")],
        [InlineKeyboardButton("🔔 Безопасность", callback_data="profile_security")],
        [InlineKeyboardButton("🌐 Часовой пояс", callback_data="profile_timezone")],
        [InlineKeyboardButton("🔙 Назад", callback_data="profile_back")],
    ]
    if config.get_webapp_url():
        rows.insert(
            1,
            [
                InlineKeyboardButton(
                    "📝 Заполнить форму",
                    web_app=WebAppInfo(reminder_handlers.build_webapp_url("/profile")),
                )
            ],
        )
    keyboard = InlineKeyboardMarkup(rows)
    await message.reply_text(msg, reply_markup=keyboard)


async def profile_webapp_save(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Save profile data sent from the web app."""
    api, ApiException, ProfileModel = get_api()
    eff_msg = update.effective_message
    if eff_msg is None:
        return
    web_app = getattr(eff_msg, "web_app_data", None)
    error_msg = "⚠️ Некорректные данные из WebApp."
    if web_app is None:
        await eff_msg.reply_text(error_msg, reply_markup=menu_keyboard())
        return
    raw = web_app.data
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        await eff_msg.reply_text(error_msg, reply_markup=menu_keyboard())
        return
    if {
        "icr",
        "cf",
        "target",
        "low",
        "high",
    } - data.keys():
        await eff_msg.reply_text(error_msg, reply_markup=menu_keyboard())
        return
    try:
        icr = float(str(data["icr"]).replace(",", "."))
        cf = float(str(data["cf"]).replace(",", "."))
        target = float(str(data["target"]).replace(",", "."))
        low = float(str(data["low"]).replace(",", "."))
        high = float(str(data["high"]).replace(",", "."))
    except ValueError:
        await eff_msg.reply_text(error_msg, reply_markup=menu_keyboard())
        return
    user = update.effective_user
    if user is None:
        await eff_msg.reply_text(error_msg, reply_markup=menu_keyboard())
        return
    user_id = user.id
    ok, err = post_profile(
        api,
        ApiException,
        ProfileModel,
        user_id,
        icr,
        cf,
        target,
        low,
        high,
    )
    if not ok:
        await eff_msg.reply_text(
            err or "⚠️ Не удалось сохранить профиль.",
            reply_markup=menu_keyboard(),
        )
        return
    await eff_msg.reply_text(
        "✅ Профиль обновлён:\n"
        f"• ИКХ: {icr} г/ед.\n"
        f"• КЧ: {cf} ммоль/л\n"
        f"• Целевой сахар: {target} ммоль/л\n"
        f"• Низкий порог: {low} ммоль/л\n"
        f"• Высокий порог: {high} ммоль/л",
        reply_markup=menu_keyboard(),
    )


async def profile_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel profile creation conversation."""
    message = update.message
    if message is not None:
        await message.reply_text("Отменено.", reply_markup=menu_keyboard())
    return END


async def profile_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return to main menu from profile view."""
    query = update.callback_query
    if query is None or query.message is None:
        return
    await query.answer()
    await query.message.delete()
    await query.message.reply_text("📋 Выберите действие:", reply_markup=menu_keyboard())


async def profile_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user to enter timezone."""
    query = update.callback_query
    if query is None or query.message is None:
        return END
    await query.answer()
    await query.message.reply_text(
        "Введите ваш часовой пояс (например Europe/Moscow):",
        reply_markup=back_keyboard,
    )
    button = build_timezone_webapp_button()
    if button:
        keyboard = InlineKeyboardMarkup([[button]])
        await query.message.reply_text("Можно определить автоматически:", reply_markup=keyboard)
    return PROFILE_TZ


async def profile_timezone_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save user timezone from input."""
    message = update.message
    if message is None:
        return END
    web_app = getattr(message, "web_app_data", None)
    if web_app is not None:
        raw = web_app.data
    elif message.text is not None:
        raw = message.text.strip()
    else:
        return END
    if "назад" in raw.lower():
        return await profile_cancel(update, context)
    try:
        ZoneInfo(raw)
    except ZoneInfoNotFoundError:
        logger.warning("Invalid timezone provided: %s", raw)
        await message.reply_text(
            "Некорректный часовой пояс. Пример: Europe/Moscow",
            reply_markup=back_keyboard,
        )
        button = build_timezone_webapp_button()
        if button:
            keyboard = InlineKeyboardMarkup([[button]])
            await message.reply_text("Можно определить автоматически:", reply_markup=keyboard)
        return PROFILE_TZ
    user = update.effective_user
    if user is None:
        return END
    user_id = user.id

    def db_set_timezone(session: Session) -> tuple[bool, bool]:
        return set_timezone(session, user_id, raw)

    if run_db is None:
        with SessionLocal() as session:
            exists, ok = db_set_timezone(session)
    else:
        exists, ok = await run_db(db_set_timezone, sessionmaker=SessionLocal)
    if not exists:
        await message.reply_text("Профиль не найден.", reply_markup=menu_keyboard())
        return END
    if not ok:
        await message.reply_text(
            "⚠️ Не удалось обновить часовой пояс.",
            reply_markup=menu_keyboard(),
        )
        return END
    await message.reply_text("✅ Часовой пояс обновлён.", reply_markup=menu_keyboard())
    return END


def _security_db(session: Session, user_id: int, action: str | None) -> dict[str, object]:
    profile = session.get(Profile, user_id)
    user = session.get(User, user_id)
    if not profile:
        return {"found": False}
    changed = False
    if action == "low_inc":
        new = (profile.low_threshold or 0) + 0.5
        if profile.high_threshold is None or new < profile.high_threshold:
            profile.low_threshold = new
            changed = True
    elif action == "low_dec":
        new = (profile.low_threshold or 0) - 0.5
        if new > 0:
            profile.low_threshold = new
            changed = True
    elif action == "high_inc":
        new = (profile.high_threshold or 0) + 0.5
        profile.high_threshold = new
        changed = True
    elif action == "high_dec":
        new = (profile.high_threshold or 0) - 0.5
        if profile.low_threshold is None or new > profile.low_threshold:
            profile.high_threshold = new
            changed = True
    elif action == "toggle_sos":
        profile.sos_alerts_enabled = not profile.sos_alerts_enabled
        changed = True

    commit_ok = True
    alert_sugar = None
    if changed:
        try:
            commit(session)
            alert = (
                session.query(Alert)
                .filter_by(user_id=user_id)
                .order_by(Alert.ts.desc())
                .first()
            )
            alert_sugar = alert.sugar if alert else None
        except CommitError:
            commit_ok = False

    rems = session.query(Reminder).filter_by(telegram_id=user_id).all()
    rem_text = "\n".join(f"{r.id}. {reminder_handlers._describe(r, user)}" for r in rems) if rems else "нет"
    return {
        "found": True,
        "commit_ok": commit_ok,
        "low": float(profile.low_threshold or 0),
        "high": float(profile.high_threshold or 0),
        "sos_enabled": profile.sos_alerts_enabled,
        "rem_text": rem_text,
        "alert_sugar": float(alert_sugar) if alert_sugar is not None else None,
    }


async def profile_security(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display and modify security settings."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    q_message = query.message
    if q_message is None:
        return
    user = update.effective_user
    if user is None:
        return
    await query.answer()
    user_id = user.id
    action = query.data.split(":", 1)[1] if ":" in query.data else None

    if action == "sos_contact":
        from services.api.app.diabetes.handlers import sos_handlers

        await sos_handlers.sos_contact_start(update, context)
        return
    if action == "add" and config.get_webapp_url():
        button = InlineKeyboardButton(
            "📝 Новое",
            web_app=WebAppInfo(reminder_handlers.build_webapp_url("/reminders")),
        )
        keyboard = InlineKeyboardMarkup([[button]])
        await q_message.reply_text("Создать напоминание:", reply_markup=keyboard)
    elif action == "del":
        await reminder_handlers.delete_reminder(update, context)

    def db_security(session: Session) -> dict[str, object]:
        return _security_db(session, user_id, action)

    if run_db is None:
        with SessionLocal() as session:
            result = db_security(session)
    else:
        result = await run_db(db_security, sessionmaker=SessionLocal)
    if not result.get("found"):
        await query.edit_message_text("Профиль не найден.")
        return
    if not result.get("commit_ok", True):
        await q_message.reply_text(
            "⚠️ Не удалось сохранить настройки.",
            reply_markup=menu_keyboard(),
        )
        return
    alert_sugar = result.get("alert_sugar")
    if isinstance(alert_sugar, (int, float, str)):
        job_queue = cast(DefaultJobQueue, context.application.job_queue)
        await evaluate_sugar(user_id, float(alert_sugar), job_queue)

    low = result["low"]
    high = result["high"]
    sos = "вкл" if result["sos_enabled"] else "выкл"
    rem_text = result["rem_text"]
    text = (
        "🔐 Настройки безопасности:\n"
        f"Низкий порог: {low:.1f} ммоль/л\n"
        f"Высокий порог: {high:.1f} ммоль/л\n"
        f"SOS-уведомления: {sos}\n\n"
        f"⏰ Напоминания:\n{rem_text}"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Низкий -0.5", callback_data="profile_security:low_dec"),
                InlineKeyboardButton("Низкий +0.5", callback_data="profile_security:low_inc"),
            ],
            [
                InlineKeyboardButton("Высокий -0.5", callback_data="profile_security:high_dec"),
                InlineKeyboardButton("Высокий +0.5", callback_data="profile_security:high_inc"),
            ],
            [
                InlineKeyboardButton(
                    f"SOS-уведомления: {'off' if result['sos_enabled'] else 'on'}",
                    callback_data="profile_security:toggle_sos",
                )
            ],
            [InlineKeyboardButton("SOS контакт", callback_data="profile_security:sos_contact")],
            [
                InlineKeyboardButton("➕ Добавить", callback_data="profile_security:add"),
                InlineKeyboardButton("🗑 Удалить", callback_data="profile_security:del"),
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data="profile_back")],
        ]
    )
    await query.edit_message_text(text, reply_markup=keyboard)


async def profile_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start step-by-step profile setup."""
    query = update.callback_query
    if query is None or query.message is None:
        return END
    await query.answer()
    await query.message.delete()
    await query.message.reply_text(
        "Введите коэффициент ИКХ (г/ед.) — сколько граммов углеводов покрывает 1 ед. быстрого инсулина:",
        reply_markup=back_keyboard,
    )
    return PROFILE_ICR


async def profile_icr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle ICR input."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        context.user_data = {}
        user_data_raw = context.user_data
    assert user_data_raw is not None
    user_data = cast(UserData, user_data_raw)
    context.user_data = user_data
    message = update.message
    if message is None or message.text is None:
        return END
    raw_text = message.text.strip()
    if "назад" in raw_text.lower():
        return await profile_cancel(update, context)
    text = raw_text.replace(",", ".")
    try:
        icr = float(text)
    except ValueError:
        await message.reply_text("Введите ИКХ числом.", reply_markup=back_keyboard)
        return PROFILE_ICR
    if icr <= 0:
        await message.reply_text(MSG_ICR_GT0, reply_markup=back_keyboard)
        return PROFILE_ICR
    user_data["profile_icr"] = icr
    await message.reply_text(
        "Введите коэффициент чувствительности (КЧ) ммоль/л — на сколько ммоль/л 1 ед. инсулина снижает сахар:",
        reply_markup=back_keyboard,
    )
    return PROFILE_CF


async def profile_cf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle CF input."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        context.user_data = {}
        user_data_raw = context.user_data
    assert user_data_raw is not None
    user_data = cast(UserData, user_data_raw)
    context.user_data = user_data
    message = update.message
    if message is None or message.text is None:
        return END
    raw_text = message.text.strip()
    if "назад" in raw_text.lower():
        await message.reply_text(
            "Введите коэффициент ИКХ (г/ед.) — сколько граммов углеводов покрывает 1 ед. быстрого инсулина:",
            reply_markup=back_keyboard,
        )
        return PROFILE_ICR
    text = raw_text.replace(",", ".")
    try:
        cf = float(text)
    except ValueError:
        await message.reply_text("Введите КЧ числом.", reply_markup=back_keyboard)
        return PROFILE_CF
    if cf <= 0:
        await message.reply_text(MSG_CF_GT0, reply_markup=back_keyboard)
        return PROFILE_CF
    user_data["profile_cf"] = cf
    await message.reply_text(
        "Введите целевой уровень сахара (ммоль/л) — к какому значению вы стремитесь:",
        reply_markup=back_keyboard,
    )
    return PROFILE_TARGET


async def profile_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle target BG input."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        context.user_data = {}
        user_data_raw = context.user_data
    assert user_data_raw is not None
    user_data = cast(UserData, user_data_raw)
    context.user_data = user_data
    message = update.message
    if message is None or message.text is None:
        return END
    raw_text = message.text.strip()
    if "назад" in raw_text.lower():
        await message.reply_text(
            "Введите коэффициент чувствительности (КЧ) ммоль/л — на сколько ммоль/л 1 ед. инсулина снижает сахар:",
            reply_markup=back_keyboard,
        )
        return PROFILE_CF
    text = raw_text.replace(",", ".")
    try:
        target = float(text)
    except ValueError:
        await message.reply_text("Введите целевой сахар числом.", reply_markup=back_keyboard)
        return PROFILE_TARGET
    if target <= 0:
        await message.reply_text(MSG_TARGET_GT0, reply_markup=back_keyboard)
        return PROFILE_TARGET
    user_data["profile_target"] = target
    await message.reply_text(
        "Введите нижний порог сахара (ммоль/л) — ниже него бот предупредит о гипогликемии:",
        reply_markup=back_keyboard,
    )
    return PROFILE_LOW


async def profile_low(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle low threshold input."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        context.user_data = {}
        user_data_raw = context.user_data
    assert user_data_raw is not None
    user_data = cast(UserData, user_data_raw)
    context.user_data = user_data
    message = update.message
    if message is None or message.text is None:
        return END
    raw_text = message.text.strip()
    if "назад" in raw_text.lower():
        await message.reply_text(
            "Введите целевой уровень сахара (ммоль/л) — к какому значению вы стремитесь:",
            reply_markup=back_keyboard,
        )
        return PROFILE_TARGET
    text = raw_text.replace(",", ".")
    try:
        low = float(text)
    except ValueError:
        await message.reply_text("Введите нижний порог числом.", reply_markup=back_keyboard)
        return PROFILE_LOW
    if low <= 0:
        await message.reply_text(MSG_LOW_GT0, reply_markup=back_keyboard)
        return PROFILE_LOW
    user_data["profile_low"] = low
    await message.reply_text(
        "Введите верхний порог сахара (ммоль/л) — выше него бот предупредит о гипергликемии:",
        reply_markup=back_keyboard,
    )
    return PROFILE_HIGH


async def profile_high(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle high threshold input and save profile."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        context.user_data = {}
        user_data_raw = context.user_data
    assert user_data_raw is not None
    user_data = cast(UserData, user_data_raw)
    context.user_data = user_data
    message = update.message
    if message is None or message.text is None:
        return END
    raw_text = message.text.strip()
    if "назад" in raw_text.lower():
        await message.reply_text(
            "Введите нижний порог сахара (ммоль/л) — ниже него бот предупредит о гипогликемии:",
            reply_markup=back_keyboard,
        )
        return PROFILE_LOW
    text = raw_text.replace(",", ".")
    try:
        high = float(text)
    except ValueError:
        await message.reply_text("Введите верхний порог числом.", reply_markup=back_keyboard)
        return PROFILE_HIGH
    low = user_data.get("profile_low")
    if high <= 0 or low is None or high <= low:
        await message.reply_text(
            MSG_HIGH_GT_LOW,
            reply_markup=back_keyboard,
        )
        return PROFILE_HIGH
    icr = user_data.pop("profile_icr", None)
    cf = user_data.pop("profile_cf", None)
    target = user_data.pop("profile_target", None)
    user_data.pop("profile_low", None)
    if icr is None or cf is None or target is None:
        await message.reply_text("⚠️ Не хватает данных для сохранения профиля. Пожалуйста, начните заново.")
        return END
    user = update.effective_user
    if user is None:
        await message.reply_text("⚠️ Не удалось определить пользователя.")
        return END
    user_id = user.id

    def db_save_profile(session: Session) -> bool:
        return bool(
            save_profile(
                session,
                user_id,
                icr,
                cf,
                target,
                low,
                high,
            )
        )

    if run_db is None:
        with SessionLocal() as session:
            ok = db_save_profile(session)
    else:
        ok = await run_db(
            db_save_profile,
            sessionmaker=SessionLocal,
        )
    if not ok:
        await message.reply_text("⚠️ Не удалось сохранить профиль.")
        return END
    warning_msg = ""
    if icr > 8 or cf < 3:
        warning_msg = (
            "\n⚠️ Проверьте, пожалуйста: возможно, вы перепутали местами ИКХ и КЧ.\n"
            f"• Вы ввели ИКХ = {icr} г/ед. (высоковато)\n"
            f"• КЧ = {cf} ммоль/л (низковато)\n\n"
            "Если вы хотели ввести наоборот, отправьте:\n"
            f"/profile {cf} {icr} {target} {low} {high}\n"
            f"(ИКХ {cf}, КЧ {icr}, целевой {target}, низкий {low}, высокий {high})\n"
        )
    await message.reply_text(
        "✅ Профиль обновлён:\n"
        f"• ИКХ: {icr} г/ед.\n"
        f"• КЧ: {cf} ммоль/л\n"
        f"• Целевой сахар: {target} ммоль/л\n"
        f"• Низкий порог: {low} ммоль/л\n"
        f"• Высокий порог: {high} ммоль/л" + warning_msg,
        reply_markup=menu_keyboard(),
    )
    return END


async def _photo_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from .. import _cancel_then
    from ..dose_calc import photo_prompt

    handler = _cancel_then(photo_prompt)
    await handler(update, context)
    return END


async def _profile_edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await profile_edit(update, context)


async def _profile_timezone_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await profile_timezone(update, context)


profile_conv = ConversationHandler(
    entry_points=[
        CommandHandler("profile", profile_command),
        CallbackQueryNoWarnHandler(_profile_edit_entry, pattern="^profile_edit$"),
        CallbackQueryNoWarnHandler(_profile_timezone_entry, pattern="^profile_timezone$"),
    ],
    states={
        PROFILE_ICR: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_icr)],
        PROFILE_CF: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_cf)],
        PROFILE_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_target)],
        PROFILE_LOW: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_low)],
        PROFILE_HIGH: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_high)],
        PROFILE_TZ: [
            MessageHandler(
                (filters.TEXT & ~filters.COMMAND) | filters.StatusUpdate.WEB_APP_DATA,
                profile_timezone_save,
            )
        ],
    },
    fallbacks=[
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), profile_cancel),
        CommandHandler("cancel", profile_cancel),
        MessageHandler(filters.Regex(f"^{PHOTO_BUTTON_TEXT}$"), _photo_fallback),
    ],
    # Subsequent steps depend on ``MessageHandler`` for text inputs. Enabling
    # ``per_message=True`` would store state per message and reset the
    # conversation after each reply, so we keep per-chat tracking.
    per_message=False,
)


profile_webapp_handler = MessageHandler(filters.StatusUpdate.WEB_APP_DATA, profile_webapp_save)


__all__ = [
    "get_api",
    "save_profile",
    "set_timezone",
    "fetch_profile",
    "post_profile",
    "parse_profile_args",
    "profile_command",
    "profile_view",
    "profile_cancel",
    "profile_back",
    "profile_security",
    "profile_timezone",
    "profile_edit",
    "profile_conv",
    "profile_webapp_save",
    "profile_webapp_handler",
    "back_keyboard",
    "MSG_ICR_GT0",
    "MSG_CF_GT0",
    "MSG_TARGET_GT0",
    "MSG_LOW_GT0",
    "MSG_HIGH_GT_LOW",
    "PROFILE_ICR",
    "PROFILE_CF",
    "PROFILE_TARGET",
    "PROFILE_LOW",
    "PROFILE_HIGH",
    "PROFILE_TZ",
    "END",
]
