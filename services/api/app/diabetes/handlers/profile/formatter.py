"""Utilities for formatting profile view message and keyboard."""

from __future__ import annotations

from datetime import time as dt_time
from typing import cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def profile_view_formatter(
    profile: object | None,
    webapp_button: list[InlineKeyboardButton] | None = None,
) -> tuple[str, InlineKeyboardMarkup | None]:
    """Build message text and keyboard for profile view."""
    if not profile:
        text = "Ваш профиль пока не настроен.\n\nНастройки профиля доступны в приложении."
        if webapp_button is not None:
            text += " Нажмите кнопку ниже, чтобы открыть и обновить данные."
            keyboard = InlineKeyboardMarkup([webapp_button])
        else:
            keyboard = None
        return text, keyboard

    icr = cast(object | None, getattr(profile, "icr", None))
    cf = cast(object | None, getattr(profile, "cf", None))
    target = cast(object | None, getattr(profile, "target", None))
    low = cast(object | None, getattr(profile, "low", None))
    high = cast(object | None, getattr(profile, "high", None))
    dia = cast(object | None, getattr(profile, "dia", None))
    round_step = cast(object | None, getattr(profile, "round_step", None))
    carb_units = cast(object | None, getattr(profile, "carb_units", None))
    grams_per_xe = cast(object | None, getattr(profile, "grams_per_xe", None))
    therapy_type = cast(object | None, getattr(profile, "therapy_type", None))
    rapid_insulin_type = cast(object | None, getattr(profile, "rapid_insulin_type", None))
    if rapid_insulin_type is None:
        rapid_insulin_type = cast(object | None, getattr(profile, "insulin_type", None))
    prebolus_min = cast(object | None, getattr(profile, "prebolus_min", None))
    max_bolus = cast(object | None, getattr(profile, "max_bolus", None))
    postmeal_check_min = cast(object | None, getattr(profile, "postmeal_check_min", None))
    quiet_start = cast(dt_time | dict[str, int] | None, getattr(profile, "quiet_start", None))
    quiet_end = cast(dt_time | dict[str, int] | None, getattr(profile, "quiet_end", None))
    if isinstance(quiet_start, dict):
        quiet_start = dt_time(**quiet_start)
    if isinstance(quiet_end, dict):
        quiet_end = dt_time(**quiet_end)
    timezone = cast(object | None, getattr(profile, "timezone", None))
    sos_contact = cast(object | None, getattr(profile, "sos_contact", None))
    sos_alerts_enabled = cast(bool | None, getattr(profile, "sos_alerts_enabled", None))

    bolus_lines = []
    if icr is not None:
        bolus_lines.append(f"• ИКХ: {icr} г/ед.")
    if cf is not None:
        bolus_lines.append(f"• КЧ: {cf} ммоль/л")
    if target is not None:
        bolus_lines.append(f"• Целевой сахар: {target} ммоль/л")
    if low is not None:
        bolus_lines.append(f"• Низкий порог: {low} ммоль/л")
    if high is not None:
        bolus_lines.append(f"• Высокий порог: {high} ммоль/л")
    if dia is not None:
        bolus_lines.append(f"• ДиА: {dia} ч")
    if round_step is not None:
        bolus_lines.append(f"• Округление: {round_step} ед.")
    if therapy_type is not None:
        bolus_lines.append(f"• Терапия: {therapy_type}")
    if rapid_insulin_type is not None:
        bolus_lines.append(f"• Инсулин: {rapid_insulin_type}")
    if prebolus_min is not None:
        bolus_lines.append(f"• Преболюс: {prebolus_min} мин")
    if max_bolus is not None:
        bolus_lines.append(f"• Макс. болюс: {max_bolus}")
    if postmeal_check_min is not None:
        bolus_lines.append(f"• Проверка после еды: {postmeal_check_min} мин")

    carb_lines: list[str] = []
    if carb_units is not None:
        carb_lines.append(f"• Ед. углеводов: {carb_units}")
    if grams_per_xe is not None:
        carb_lines.append(f"• Грамм/ХЕ: {grams_per_xe}")

    safety_lines: list[str] = []
    if quiet_start and quiet_end:
        qs = quiet_start.strftime("%H:%M") if hasattr(quiet_start, "strftime") else str(quiet_start)
        qe = quiet_end.strftime("%H:%M") if hasattr(quiet_end, "strftime") else str(quiet_end)
        safety_lines.append(f"• Тихий режим: {qs}-{qe}")
    if timezone is not None:
        safety_lines.append(f"• Часовой пояс: {timezone}")
    if sos_contact is not None:
        safety_lines.append(f"• SOS контакт: {sos_contact}")
    if sos_alerts_enabled is not None:
        state = "вкл" if sos_alerts_enabled else "выкл"
        safety_lines.append(f"• SOS оповещения: {state}")

    sections: list[str] = []
    if bolus_lines:
        sections.append("💉 *Болус*\n" + "\n".join(bolus_lines))
    if carb_lines:
        sections.append("🍽 *Углеводы*\n" + "\n".join(carb_lines))
    if safety_lines:
        sections.append("🛡 *Безопасность*\n" + "\n".join(safety_lines))

    msg = "📄 Ваш профиль:\n\n" + "\n\n".join(sections)
    rows = [
        [InlineKeyboardButton("✏️ Изменить", callback_data="profile_edit")],
        [InlineKeyboardButton("🔔 Безопасность", callback_data="profile_security")],
        [InlineKeyboardButton("🔙 Назад", callback_data="profile_back")],
    ]
    if webapp_button is not None:
        rows.insert(1, webapp_button)
    keyboard = InlineKeyboardMarkup(rows)
    return msg, keyboard
