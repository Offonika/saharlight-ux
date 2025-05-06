# bot.py
import os
import re
import asyncio
import time
import logging
# bot.py  – верхняя часть (где уже есть import datetime)
from datetime import datetime, timezone   # ← добавили timezone

from gpt_command_parser import parse_command
from telegram.ext import MessageHandler, filters
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
from db import SessionLocal, init_db, User, Profile, Entry
from gpt_client import create_thread, send_message, client
from functions import PatientProfile, calc_bolus
from config import TELEGRAM_TOKEN
from datetime import datetime
from sqlalchemy import DateTime, func
from db import SessionLocal, Entry, Profile, User, init_db
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import func          # уже нужен для фильтра по дате# ▸ bot.py  (положите рядом с остальными async‑хендлерами)
from pathlib import Path


PROFILE_ICR, PROFILE_CF, PROFILE_TARGET         = range(0, 3)    # 0,1,2
DOSE_METHOD, DOSE_XE, DOSE_SUGAR, DOSE_CARBS    = range(3, 7)    # 3,4,5,6
PHOTO_SUGAR                                     = 7              # после DOSE_CARBS
SUGAR_VAL                                       = 8              # конверсация /sugar
# (подтверждение/переопределение дозы при желании  можно сделать 9 и 10)

WAITING_GPT_FLAG = "waiting_gpt_response"

# Клавиатура для выбора метода ввода
dose_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📷 Фото для оценки")],
        [KeyboardButton("✏️ Ввести углеводы (г)")],
        [KeyboardButton("🔢 Ввести ХЕ")],
        [KeyboardButton("❌ Отмена")],
    ],
    resize_keyboard=True
)

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📷 Фото еды")], 
        [KeyboardButton("💉 Доза инсулина"), KeyboardButton("📊 История")],
        [KeyboardButton("📄 Мой профиль"), KeyboardButton("🔄 Изменить профиль")],
        [KeyboardButton("🔁 Сброс")]
    ],
    resize_keyboard=True
)

# В начале файла (после импортов) настройка логгера:
logging.basicConfig(filename='gpt_responses.log', level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)





# bot.py  (показываю целиком изменённую функцию)

import re
from datetime import datetime, time as dtime
# ...

# bot.py
from datetime import datetime, time as dtime, timezone
# … остальной импорт …

# ──────────────────────────────────────────────────────────────
async def freeform_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text.strip()
    user_id  = update.effective_user.id
    logger.info(f"FREEFORM raw='{raw_text}'  user={user_id}")

    parsed = await parse_command(raw_text)
    logger.info(f"FREEFORM parsed={parsed}")

    # если парсер не дал JSON‑команду — просто выходим
    if not parsed or parsed.get("action") != "add_entry":
        return

    fields      = parsed["fields"]
    entry_date  = parsed.get("entry_date")   # ISO‑строка или None
    time_str    = parsed.get("time")         # "HH:MM" или None

    # ── определяем event_time ─────────────────────────────────
    if entry_date:
        # полная дата уже указана GPT
        try:
            event_dt = datetime.fromisoformat(entry_date).replace(tzinfo=timezone.utc)
        except ValueError:
            # формат кривой — откатываемся к «сейчас»
            event_dt = datetime.now(timezone.utc)
       
    elif time_str:
        # время указано без даты – считаем, что это ЛОКАЛЬНОЕ время пользователя,
        # поэтому НЕ задаём tzinfo
        try:
            hh, mm = map(int, time_str.split(":"))
            today  = datetime.now().date()
            event_dt = datetime.combine(today, dtime(hh, mm))   # ← без tzinfo
        except Exception:
            event_dt = datetime.now()



    else:
        # ничего не пришло → текущее время
        event_dt = datetime.now(timezone.utc)

    # ── создаём объект записи ─────────────────────────────────
    entry = Entry(
        telegram_id  = user_id,
        event_time   = event_dt,
        xe           = fields.get("xe"),
        carbs_g      = fields.get("carbs_g"),
        dose         = fields.get("dose"),
        sugar_before = fields.get("sugar_before"),
    )

    # ── сохраняем в БД ────────────────────────────────────────
    session = SessionLocal()
    session.add(entry)
    session.commit()

    # копируем нужные поля, пока объект ещё привязан к сессии
    evt_time   = entry.event_time.astimezone()   # локальная зона TG‑юзера
    xe_val     = entry.xe
    carbs_val  = entry.carbs_g
    dose_val   = entry.dose
    sugar_val  = entry.sugar_before
    session.close()

    # ── формируем ответ ───────────────────────────────────────
    date_str   = evt_time.strftime("%d.%m %H:%M")
    xe_part    = f"{xe_val} ХЕ"               if xe_val   is not None else ""
    carb_part  = f"{carbs_val:.0f} г углеводов" if carbs_val is not None else ""
    dose_part  = f"Инсулин: {dose_val} ед"    if dose_val is not None else ""
    sugar_part = f"Сахар: {sugar_val} ммоль/л" if sugar_val is not None else ""

    lines = "  \n- ".join(filter(None, [xe_part or carb_part,
                                        dose_part,
                                        sugar_part]))
    reply = f"Записано:\n\n{date_str}  \n- {lines}"
    await update.message.reply_text(reply, reply_markup=menu_keyboard)


def extract_nutrition_info(text: str):
    """
    Ищет в тексте:
      • «Углеводы: 37 г ± 3 г»  → carbs = 37
      • «ХЕ: 3,1 ± 0,2»         → xe    = 3.1
      • диапазон «20–25 г»      → carbs = среднее
      • диапазон «3–4 ХЕ»       → xe    = среднее
    Возвращает (carbs_g, xe)
    """
    carbs = xe = None
    # --- новый строгий формат со знаком ± ---
    m = re.search(r"углевод[^\d]*:\s*([\d.,]+)\s*г", text, re.IGNORECASE)
    if m:
        carbs = float(m.group(1).replace(",", "."))

    m = re.search(r"\bх[еe][^\d]*:\s*([\d.,]+)", text, re.IGNORECASE)
    if m:
        xe = float(m.group(1).replace(",", "."))

    # --- диапазоны «20–25 г» / «3–4 ХЕ» ---
    if carbs is None:
        rng = re.search(r"(\d+[.,]?\d*)\s*[–-]\s*(\d+[.,]?\d*)\s*г", text, re.IGNORECASE)
        if rng:
            carbs = (float(rng.group(1).replace(",", ".")) +
                     float(rng.group(2).replace(",", "."))) / 2

    if xe is None:
        rng = re.search(r"(\d+[.,]?\d*)\s*[–-]\s*(\d+[.,]?\d*)\s*(?:ХЕ|XE)", text, re.IGNORECASE)
        if rng:
            xe = (float(rng.group(1).replace(",", ".")) +
                  float(rng.group(2).replace(",", "."))) / 2

    return carbs, xe

# ▸ bot.py  (положите рядом с остальными async‑хендлерами)
async def apply_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "edit_id" not in context.user_data:    # нет режима редактирования
        return

    text = update.message.text.lower()
    parts = dict(re.findall(r"(\w+)\s*=\s*([\d.]+)", text))
    if not parts:
        await update.message.reply_text("Не вижу ни одного поля для изменения.")
        return

    with SessionLocal() as s:
        entry = s.get(Entry, context.user_data["edit_id"])
        if not entry:
            await update.message.reply_text("Запись уже удалена.")
            context.user_data.pop("edit_id")
            return

        # обновляем поля, если присутствуют
        if "xe" in parts:    entry.xe           = float(parts["xe"])
        if "carbs" in parts: entry.carbs_g      = float(parts["carbs"])
        if "dose" in parts:  entry.dose         = float(parts["dose"])
        if "сахар" in parts or "sugar" in parts:
            entry.sugar_before = float(parts.get("сахар") or parts["sugar"])
        entry.updated_at = datetime.utcnow()
        s.commit()

    context.user_data.pop("edit_id")
    await update.message.reply_text("✅ Запись обновлена!")

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает inline‑кнопки из /history."""
    query   = update.callback_query
    await query.answer()                       # ← обязательный ACK
    action, entry_id = query.data.split(":", 1)

    with SessionLocal() as s:
        entry = s.get(Entry, int(entry_id))
        if not entry:
            await query.edit_message_text("Запись не найдена (уже удалена).")
            return

        # ---- УДАЛЕНИЕ ----------------------------------------------------
        if action == "del":
            s.delete(entry)
            s.commit()
            await query.edit_message_text("❌ Запись удалена.")
            return

        # ---- РЕДАКТИРОВАНИЕ ----------------------------------------------
        if action == "edit":
            context.user_data["edit_id"] = entry.id
            txt = (
                "Отправьте новое сообщение в формате:\n"
                "`сахар=<ммоль/л>  xe=<ХЕ>  carbs=<г>  dose=<ед>`\n"
                "Можно указывать не все поля (что прописано — то и поменяется).",
            )
            await query.edit_message_text("\n".join(txt), parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    session = SessionLocal()
    user_id = update.effective_user.id
    user = session.get(User, user_id)
    if not user:
        thread_id = create_thread()
        user = User(telegram_id=user_id, thread_id=thread_id)
        session.add(user)
        session.commit()
        await update.message.reply_text("Добро пожаловать! Профиль создан.", reply_markup=menu_keyboard)
    else:
        await update.message.reply_text("С возвращением!", reply_markup=menu_keyboard)
    session.close()

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Выберите действие:", reply_markup=menu_keyboard)

async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    session = SessionLocal()
    user_id = update.effective_user.id
    session.query(Entry).filter_by(telegram_id=user_id).delete()
    session.query(Profile).filter_by(telegram_id=user_id).delete()
    session.commit()
    session.close()
    await update.message.reply_text("Профиль и история удалены. Вы можете начать заново.", reply_markup=menu_keyboard)

# === Профиль ===
async def profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()
    user_id = update.effective_user.id
    profile = session.get(Profile, user_id)
    session.close()
    
    current_value = f"(текущее: {profile.icr} г/ед.)" if profile and profile.icr else ""
    await update.message.reply_text(
        f"Введите ИКХ (сколько г углеводов на 1 ед. инсулина) {current_value}:"
    )
    return PROFILE_ICR

async def profile_icr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['icr'] = float(update.message.text)
        
        session = SessionLocal()
        profile = session.get(Profile, update.effective_user.id)
        session.close()

        current_value = f"(текущее: {profile.cf} ммоль/л)" if profile and profile.cf else ""
        await update.message.reply_text(
            f"Введите коэффициент коррекции (КЧ) {current_value}:"
        )
        return PROFILE_CF
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число.")
        return PROFILE_ICR

async def profile_cf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['cf'] = float(update.message.text)

        session = SessionLocal()
        profile = session.get(Profile, update.effective_user.id)
        session.close()

        current_value = f"(текущее: {profile.target_bg} ммоль/л)" if profile and profile.target_bg else ""
        await update.message.reply_text(
            f"Введите целевой уровень сахара {current_value}:"
        )
        return PROFILE_TARGET
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число.")
        return PROFILE_CF

async def profile_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['target'] = float(update.message.text)
        session = SessionLocal()
        user_id = update.effective_user.id
        prof = session.get(Profile, user_id)
        if not prof:
            prof = Profile(telegram_id=user_id)
            session.add(prof)
        prof.icr = context.user_data['icr']
        prof.cf = context.user_data['cf']
        prof.target_bg = context.user_data['target']
        session.commit()
        session.close()
        await update.message.reply_text("✅ Профиль сохранён.", reply_markup=menu_keyboard)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число.")
        return PROFILE_TARGET
    
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 3:
        await update.message.reply_text(
            "❗ Формат команды:\n"
            "/profile <ИКХ> <КЧ> <целевой>\n"
            "Пример: /profile 2 10 6",
            parse_mode="Markdown"
        )
        return

    try:
        icr = float(args[0])
        cf = float(args[1])
        target = float(args[2])

        # Флаги подозрения
        suspicious = False
        warning_msg = ""

        if icr > 8 or cf < 3:
            suspicious = True
            warning_msg = (
                "\n⚠️ Проверьте, пожалуйста: возможно, вы перепутали местами ИКХ и КЧ.\n"
                f"• Вы ввели ИКХ = {icr} ммоль/л (высоковато)\n"
                f"• КЧ = {cf} г/ед. (низковато)\n\n"
                "Если вы хотели ввести наоборот, отправьте:\n"
                f"/profile {cf} {icr} {target}\n"
            )

        session = SessionLocal()
        user_id = update.effective_user.id
        prof = session.get(Profile, user_id)
        if not prof:
            prof = Profile(telegram_id=user_id)
            session.add(prof)

        prof.icr = cf  # г/ед
        prof.cf = icr  # ммоль/л
        prof.target_bg = target
        session.commit()
        session.close()

        await update.message.reply_text(
            f"✅ Профиль обновлён:\n"
            f"• ИКХ: {icr} ммоль/л\n"
            f"• КЧ: {cf} г/ед.\n"
            f"• Целевой сахар: {target} ммоль/л"
            + warning_msg,
            parse_mode="Markdown"
        )

    except ValueError:
        await update.message.reply_text(
            "❗ Пожалуйста, введите корректные числа. Пример:\n/profile 2 10 6",
            parse_mode="Markdown"
        )

async def profile_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    session = SessionLocal()
    user_id = update.effective_user.id
    profile = session.get(Profile, user_id)
    session.close()

    if not profile:
        await update.message.reply_text(
            "Ваш профиль пока не настроен.\n\n"
            "Чтобы настроить профиль, введите команду:\n"
            "/profile <ИКХ> <КЧ> <целевой>\n"
            "Пример: /profile 2 10 6",
            parse_mode="Markdown"
        )
        return

    msg = (
        f"📄 Ваш профиль:\n"
        f"• ИКХ: {profile.cf} ммоль/л\n"
        f"• КЧ: {profile.icr} г/ед.\n"
        f"• Целевой сахар: {profile.target_bg} ммоль/л"
    )
    await update.message.reply_text(msg)


async def profile_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=menu_keyboard)
    return ConversationHandler.END

async def photo_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопки '📷 Фото еды'"""
    await update.message.reply_text(
        "📸 Пожалуйста, отправьте фото блюда, и я оценю углеводы и ХЕ.",
        reply_markup=menu_keyboard
    )

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Действие отменено.", reply_markup=menu_keyboard)
    return ConversationHandler.END

# === Доза ===
async def dose_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Как вы хотите получить количество углеводов?\n"
        "• 📷 Фото для оценки\n"
        "• ✏️ Ввести углеводы (г)\n"
        "• 🔢 Ввести ХЕ",
        reply_markup=dose_keyboard
    )
    return DOSE_METHOD

async def sugar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если аргумент передан сразу, сохраняем сразу
    if context.args:
        try:
            sugar = float(context.args[0].replace(",", "."))
            # Записываем в БД
            session = SessionLocal()
            entry = Entry(telegram_id=update.effective_user.id, sugar_before=sugar)
            session.add(entry); session.commit(); session.close()
            await update.message.reply_text(f"✅ Уровень сахара сохранён: {sugar} ммоль/л", reply_markup=menu_keyboard)
            return ConversationHandler.END
        except ValueError:
            await update.message.reply_text("❗ Неправильный формат. Введите число или /sugar <число>")
            return ConversationHandler.END

    # Иначе — просим ввести
    await update.message.reply_text("Введите текущий уровень сахара (ммоль/л):", reply_markup=menu_keyboard)
    return SUGAR_VAL

async def sugar_val(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sugar = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❗ Пожалуйста, введите число.")
        return SUGAR_VAL

    session = SessionLocal()
    entry = Entry(telegram_id=update.effective_user.id, sugar_before=sugar)
    session.add(entry); session.commit(); session.close()

    # Сохраним в user_data, чтобы использовать в photo→dose сценарии
    context.user_data['sugar'] = sugar

    await update.message.reply_text(f"✅ Сахар сохранён: {sugar} ммоль/л", reply_markup=menu_keyboard)
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────────
async def dose_sugar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сахара после ввода углеводов (фото/ручных/ХЕ)."""
    # 1. Сахар
    try:
        sugar = float(update.message.text.replace(",", "."))
        context.user_data["sugar"] = sugar
    except ValueError:
        await update.message.reply_text("Введите число.")
        return DOSE_SUGAR

    user_id = update.effective_user.id
    session = SessionLocal()
    profile = session.get(Profile, user_id)
    if not profile:
        session.close()
        await update.message.reply_text("Профиль не найден. Используйте /profile.")
        return ConversationHandler.END

    # копируем поля профиля ДО закрытия session
    icr, cf, target_bg = profile.icr, profile.cf, profile.target_bg

    # 2. Определяем углеводы
    last_carbs = context.user_data.get("last_carbs")
    last_photo_time = context.user_data.get("last_photo_time")
    now = time.time()

    if last_carbs is not None and last_photo_time and now - last_photo_time < 600:
        carbs, xe_val = last_carbs, None
    elif context.user_data.get("xe") is not None:
        xe_val = context.user_data["xe"]
        carbs = xe_val * 12          # 1 ХЕ = 12 г
    else:
        session.close()
        await update.message.reply_text(
            "Нет данных о количестве углеводов. Сначала отправьте фото блюда или введите углеводы вручную.",
            reply_markup=menu_keyboard
        )
        return ConversationHandler.END

    # 3. Расчёт дозы
    dose = calc_bolus(carbs, sugar, PatientProfile(icr, cf, target_bg))

    entry = Entry(
        telegram_id=user_id,
        event_time=datetime.now(timezone.utc),
        sugar_before=sugar,
        carbs_g=carbs,
        xe=xe_val,
        dose=dose
    )
    session.add(entry)
    session.commit()
    session.close()

    xe_info = f", ХЕ: {xe_val}" if xe_val is not None else ""
    await update.message.reply_text(
        f"💉 Рассчитанная доза: {dose:.1f} Ед\n"
        f"(углеводы: {carbs:.0f} г{xe_info}, сахар: {sugar} ммоль/л)\n"
        f"(профиль: ИКХ {icr}, КЧ {cf}, целевой {target_bg})",
        reply_markup=menu_keyboard
    )

    # очищаем временные данные
    for k in ("last_carbs", "last_photo_time", "xe", "sugar"):
        context.user_data.pop(k, None)

    return ConversationHandler.END
# ──────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────
# Обработчик ✏️ «Ввести углеводы (г)»
async def dose_carbs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Пользователь вводит углеводы вручную.
      1. Сохраняем количество во временный контекст.
      2. Просим ввести сахар (переход в DOSE_SUGAR).
      3. Дозу рассчитает dose_sugar после ввода сахара.
    """
    try:
        carbs_input = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число граммов углеводов.")
        return DOSE_CARBS

    # сохраняем углеводы как «последние» и помечаем время (≤10 мин)
    context.user_data["last_carbs"] = carbs_input
    context.user_data["last_photo_time"] = time.time()

    await update.message.reply_text(
        "Введите текущий уровень сахара (ммоль/л):",
        reply_markup=menu_keyboard
    )
    return DOSE_SUGAR
# ──────────────────────────────────────────────────────────────


async def dose_method_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📷 Фото для оценки":
        # Завершаем текущий диалог /dose,
        # а дальше сработает отдельный photo_conv
        await update.message.reply_text(
            "Отправьте, пожалуйста, фото блюда:",
            reply_markup=menu_keyboard
        )
        return ConversationHandler.END

    if text == "✏️ Ввести углеводы (г)":
        await update.message.reply_text(
            "Введите, пожалуйста, количество углеводов в граммах:",
            reply_markup=menu_keyboard
        )
        return DOSE_CARBS

    if text == "🔢 Ввести ХЕ":
        await update.message.reply_text(
            "Введите, пожалуйста, количество хлебных единиц (ХЕ):",
            reply_markup=menu_keyboard
        )
        return DOSE_XE

    if text == "❌ Отмена":
        await update.message.reply_text("❌ Отменено.", reply_markup=menu_keyboard)
        return ConversationHandler.END

    # Если ввели что-то не из меню
    await update.message.reply_text(
        "Пожалуйста, выберите один из пунктов на клавиатуре.",
        reply_markup=dose_keyboard
    )
    return DOSE_METHOD


async def dose_xe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        xe = float(update.message.text.replace(",", "."))
        context.user_data['xe'] = xe
        # теперь запросим сахар, дальше пойдёт обычный сценарий sugar→carbs→dose
        await update.message.reply_text("Введите текущий уровень сахара (ммоль/л):", reply_markup=menu_keyboard)
        return DOSE_SUGAR
    except ValueError:
        await update.message.reply_text("Введите число ХЕ.")
        return DOSE_XE


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    1. Скачивает фото и сохраняет на диск.
    2. Отправляет в GPT (assistant API).
    3. Извлекает углеводы / ХЕ из ответа.
    4. Сохраняет временно в user_data (до ввода сахара) или
       сразу создаёт запись, если сахар уже введён.
    """
    user_id = update.effective_user.id

        # ── 1. Скачиваем фото ───────────────────────────────────────
    path = context.user_data.pop("__file_path", None)
    if path is None:                          # обычный случай «фото»
        photo = update.message.photo[-1]
        file  = await context.bot.get_file(photo.file_id)
        os.makedirs("photos", exist_ok=True)
        path  = f"photos/{user_id}_{photo.file_unique_id}.jpg"
        await file.download_to_drive(path)


    # ── 2. Готовим промпт и отправляем в GPT ────────────────────
    session = SessionLocal()
    user    = session.get(User, user_id)
    profile = session.get(Profile, user_id)
    session.close()

    profile_text = (
        f"Профиль пользователя:\n"
        f"- ИКХ: {profile.icr} г/ед\n"
        f"- КЧ: {profile.cf} ммоль/л\n"
        f"- Целевой сахар: {profile.target_bg} ммоль/л\n"
    ) if profile else "Профиль пользователя не найден."

    run = send_message(user.thread_id, content=profile_text, image_path=path)
    await update.message.reply_text("Фото отправлено, подождите ответ ассистента…", reply_markup=menu_keyboard)

    while run.status in ("queued", "in_progress"):
        run = client.beta.threads.runs.retrieve(thread_id=user.thread_id, run_id=run.id)
        await asyncio.sleep(1)

    # ── 3. Получили ответ GPT ───────────────────────────────────
    msgs = client.beta.threads.messages.list(thread_id=user.thread_id, order="desc", limit=1).data
    if not msgs:
        await update.message.reply_text("❗ Нет ответа от ассистента.", reply_markup=menu_keyboard)
        return ConversationHandler.END

    response_text = msgs[0].content[0].text.value
    await update.message.reply_text(response_text, reply_markup=menu_keyboard)

    # Простая проверка, удалось ли GPT распознать еду
    if len(response_text.strip()) < 30:
        await update.message.reply_text("Не удалось распознать блюдо. Попробуйте другое фото.", reply_markup=menu_keyboard)
        return ConversationHandler.END

    # ── 4. Извлекаем углеводы / ХЕ ──────────────────────────────
    carbs, xe = extract_nutrition_info(response_text)
    context.user_data.update({
        "last_carbs":      carbs,
        "last_xe":         xe,
        "last_photo_time": time.time(),
        "photo_path":      path,
        "carbs":           carbs,
        "xe":              xe,
    })

    # ── 5. Если сахар уже введён — сразу сохраняем запись ───────
    sugar = context.user_data.get("sugar")
    if carbs is not None and sugar is not None and profile:
        dose = calc_bolus(carbs, sugar, PatientProfile(profile.icr, profile.cf, profile.target_bg))

        session = SessionLocal()
        event_ts = update.message.date  # ← время съёмки фото (UTC)
        entry = Entry(
            telegram_id  = user_id,
            event_time   = event_ts,
            photo_path   = path,
            carbs_g      = carbs,
            xe           = xe,
            sugar_before = sugar,
            dose         = dose
        )
        session.add(entry)
        session.commit()
        session.close()

        await update.message.reply_text(
            f"💉 Ваша доза: {dose} Ед  (углеводы: {carbs} г, сахар: {sugar} ммоль/л)",
            reply_markup=menu_keyboard
        )
        return ConversationHandler.END

    # ── 6. Иначе просим ввести сахар ────────────────────────────
    await update.message.reply_text("Введите текущий уровень сахара (ммоль/л):", reply_markup=menu_keyboard)
    return PHOTO_SUGAR
async def doc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Пользователь отправил изображение как «файл» (document‑image).
    Скачиваем оригинал и передаём в общий photo‑flow.
    """
    document = update.message.document
    # игнорируем, если вдруг пришёл pdf/zip
    if not document or not document.mime_type.startswith("image/"):
        return ConversationHandler.END

    user_id = update.effective_user.id
    # путь сохранения
    ext  = Path(document.file_name).suffix or ".jpg"
    path = f"photos/{user_id}_{document.file_unique_id}{ext}"
    os.makedirs("photos", exist_ok=True)

    file = await context.bot.get_file(document.file_id)
    await file.download_to_drive(path)

    # кладём путь и «псевдо‑фото» в update, чтобы дальше всё работало
    context.user_data["__file_path"] = path
    # чтобы код, который где‑то проверяет .photo, не упал
             # пустой список‑заглушка

    # переходим в обычный обработчик фото
    return await photo_handler(update, context)
# ────────────────────────────────────────────────────────────────
async def photo_sugar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод сахара после отправленного фото.
    Если углеводы не были распознаны, предлагает запустить /dose и вводить их вручную,
    иначе сразу вычисляет дозу, сохраняет запись и завершает сценарий.
    """
    if context.user_data.get(WAITING_GPT_FLAG):
        await update.message.reply_text("Пожалуйста, дождитесь ответа по фото.")
        return ConversationHandler.END

    # 1) Считаем введённый сахар
    try:
        sugar = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❗ Пожалуйста, введите число в формате ммоль/л.")
        return PHOTO_SUGAR

    # 2) Достаём результаты анализа фото
    carbs      = context.user_data.get("carbs")
    xe         = context.user_data.get("xe")
    photo_path = context.user_data.get("photo_path")
    user_id    = update.effective_user.id

    # 3) Если углеводы из фото не распознаны, но есть ХЕ — используем xe*profile.icr
    session = SessionLocal()
    profile = session.get(Profile, user_id)
    if not profile:
        session.close()
        await update.message.reply_text(
            "❗ Профиль не найден. Сначала задайте его командой /profile.",
            reply_markup=menu_keyboard
        )
        return ConversationHandler.END

    if carbs is None and xe is not None:
        carbs = xe * profile.icr
        xe_info = f" (расчёт по ХЕ: {xe} ХЕ × {profile.icr} г/ед.)"
    else:
        xe_info = ""

    # 4) Если углеводы всё равно не распознаны
    if carbs is None:
        session.close()
        await update.message.reply_text(
            "⚠️ Не удалось определить углеводы на фото.\n"
            "Пожалуйста, выберите '💉 Доза инсулина' или /dose и введите углеводы вручную:",
            reply_markup=menu_keyboard
        )
        return ConversationHandler.END

    # 5) Иначе — расчёт дозы
    dose = calc_bolus(carbs, sugar, PatientProfile(profile.icr, profile.cf, profile.target_bg))
    
        # Устанавливаем время события
    event_time = getattr(update.message, "date", None) or datetime.utcnow()

    entry = Entry(
        telegram_id   = user_id,
        event_time    = event_time,     # 👈 добавлено
        photo_path    = photo_path,
        carbs_g       = carbs,
        xe            = xe,
        sugar_before  = sugar,
        dose          = dose
    )



    session.add(entry)
    session.commit()
    session.close()

    # 7) Убираем временные данные
    for key in ("carbs", "xe", "photo_path"):
        context.user_data.pop(key, None)

    # 8) Отправляем результат и выходим
    await update.message.reply_text(
        f"💉 Расчёт завершён:\n"
        f"• Углеводы: {carbs} г{xe_info}\n"
        f"• Сахар: {sugar} ммоль/л\n"
        f"• Ваша доза: {dose} Ед",
        reply_markup=menu_keyboard
    )
    return ConversationHandler.END


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /history                   – последние 5 записей
    /history YYYY‑MM‑DD        – записи за конкретный день
    """
    context.user_data.clear()
    user_id = update.effective_user.id

    # ── аргумент‑дата (опционально) ──────────────────────────────
    day = None
    if context.args:
        try:
            day = datetime.fromisoformat(context.args[0]).date()
        except ValueError:
            await update.message.reply_text(
                "❗ Формат даты: YYYY-MM-DD  (пример: /history 2025-05-05)"
            )
            return

    with SessionLocal() as s:
        query = s.query(Entry).filter_by(telegram_id=user_id)
        if day:
            query = query.filter(func.date(Entry.event_time) == day)

        entries = (
            query
            .order_by(Entry.event_time.desc())
            .limit(None if day else 5)
            .all()
        )

    if not entries:
        await update.message.reply_text("История пуста.")
        return

    header = "Записи за " + str(day) if day else "Последние записи"
    await update.message.reply_text(f"📖 {header}:")

    # ── выводим каждую запись отдельным сообщением ───────────────
    for e in entries:
        when   = e.event_time.astimezone().strftime("%d.%m %H:%M")
        carbs  = f"{e.carbs_g:.0f} г" if e.carbs_g else f"{e.xe:.1f} ХЕ" if e.xe else "-"
        dose   = f"{e.dose:.1f} ед"   if e.dose else "-"
        sugar  = f"{e.sugar_before:.1f}" if e.sugar_before else "-"

        text = (
            f"🕒 {when}\n"
            f"• Сахар: {sugar} ммоль/л\n"
            f"• Углеводы: {carbs}\n"
            f"• Доза: {dose}"
        )

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✏️ Исправить", callback_data=f"edit:{e.id}"),
                InlineKeyboardButton("🗑️ Удалить",   callback_data=f"del:{e.id}")
            ]
        ])
        await update.message.reply_text(text, reply_markup=kb)

async def chat_with_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return  # Игнорировать не-текстовые сообщения
    session = SessionLocal()
    user_id = update.effective_user.id
    user = session.get(User, user_id)
    session.close()
    if not user:
        await update.message.reply_text("Сначала используйте /start.")
        return
    run = send_message(user.thread_id, content=update.message.text)
    await update.message.reply_text("Ожидаем ответ от GPT...")
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(thread_id=user.thread_id, run_id=run.id)
        await asyncio.sleep(2)
    messages = client.beta.threads.messages.list(thread_id=user.thread_id)
    reply = messages.data[0].content[0].text.value
    await update.message.reply_text(reply)

def main():
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    sugar_conv = ConversationHandler(
    entry_points=[
        CommandHandler("sugar", sugar_start),
    ],
    states={
        SUGAR_VAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, sugar_val)],
    },
    fallbacks=[CommandHandler("cancel", cancel_handler)],
)

    photo_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.PHOTO,          photo_handler),  # было
            MessageHandler(filters.Document.IMAGE, doc_handler),    # ← добавили
        ],
        states={
            PHOTO_SUGAR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, photo_sugar_handler)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
    )



    dose_conv = ConversationHandler(
    entry_points=[
        CommandHandler("dose", dose_start),
        MessageHandler(filters.Regex("^💉 Доза инсулина$"), dose_start),
    ],
    states={
        DOSE_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, dose_method_choice)],
        DOSE_XE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, dose_xe_handler)],
        DOSE_SUGAR:  [MessageHandler(filters.TEXT & ~filters.COMMAND, dose_sugar)],
        DOSE_CARBS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, dose_carbs)],
    },
    fallbacks=[CommandHandler("cancel", cancel_handler)],
)

    

    profile_conv = ConversationHandler(
        entry_points=[
            CommandHandler("profile", profile_start),
            MessageHandler(filters.Regex(r"^🔄 Изменить профиль$"), profile_start)
        ],
        states={
            PROFILE_ICR:    [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_icr)],
            PROFILE_CF:     [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_cf)],
            PROFILE_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_target)],
        },
        fallbacks=[CommandHandler("cancel", profile_cancel)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(CommandHandler("reset", reset_handler))
    app.add_handler(CommandHandler("history", history_handler))
    app.add_handler(CommandHandler("profile", profile_command))
    
    app.add_handler(MessageHandler(filters.Regex("^📄 Мой профиль$"), profile_view))
    app.add_handler(MessageHandler(filters.Regex(r"^📊 История$"), history_handler))
    app.add_handler(MessageHandler(filters.Regex(r"^❓ Мой сахар$"), sugar_start))
    app.add_handler(sugar_conv)
    app.add_handler(photo_conv)
    app.add_handler(profile_conv)
    app.add_handler(dose_conv)
    # Ловим нажатие кнопки «📷 Фото еды»
    app.add_handler(MessageHandler(filters.Regex(r"^📷 Фото еды$"), photo_request))
    app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, freeform_handler)
)
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, apply_edit))

    app.run_polling()

if __name__ == "__main__":
    main()
