# bot.py
import os
import re
import asyncio
import time
import logging
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
from db import SessionLocal, init_db, User, Profile, Entry
from gpt_client import create_thread, send_message, client
from functions import PatientProfile, calc_bolus
from config import TELEGRAM_TOKEN

# Состояния для пошагового ввода профиля и дозы
# Состояния для пошагового ввода профиля и дозы
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

async def dose_sugar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['sugar'] = float(update.message.text)
        # Проверяем, есть ли свежие углеводы с фото (меньше 10 минут назад)
        last_carbs = context.user_data.get('last_carbs')
        last_photo_time = context.user_data.get('last_photo_time')
        now = time.time()
        if last_carbs is not None and last_photo_time and now - last_photo_time < 600:
            # Используем углеводы с фото, не спрашиваем повторно
            sugar = context.user_data['sugar']
            carbs = last_carbs
            user_id = update.effective_user.id
            session = SessionLocal()
            profile = session.get(Profile, user_id)
            if not profile:
                await update.message.reply_text("Профиль не найден. Используйте /profile.")
                return ConversationHandler.END
            dose = calc_bolus(carbs, sugar, PatientProfile(profile.icr, profile.cf, profile.target_bg))
            icr = profile.icr
            cf = profile.cf
            target_bg = profile.target_bg
            entry = Entry(telegram_id=user_id, sugar_before=sugar, carbs_g=carbs, dose=dose)
            session.add(entry)
            session.commit()
            session.close()
            await update.message.reply_text(
                f"Использую углеводы с последнего фото: {carbs} г.\nВаша доза: {dose} ЕД.\n"
                f"(профиль: ИКХ {cf}, КЧ {icr}, целевой {target_bg})",
                reply_markup=menu_keyboard
            )
            # Очищаем last_carbs, чтобы не использовать их повторно случайно
            context.user_data['last_carbs'] = None
            context.user_data['last_xe'] = None
            context.user_data['last_photo_time'] = None
            return ConversationHandler.END
        # --- ДОБАВЛЕНО: если last_carbs нет, сообщаем об этом ---
        await update.message.reply_text(
            "Нет данных о количестве углеводов. Сначала отправьте фото блюда или введите углеводы вручную.",
            reply_markup=menu_keyboard
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Введите число.")
        return DOSE_SUGAR

async def dose_carbs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод количества углеводов:
    – если это продолжение после фото (awaiting_carbs_after_photo=True),
      сразу считает дозу и сохраняет запись по фото;
    – иначе — обычный сценарий «/dose»: сахар уже записан, задаются углеводы.
    """
    try:
        # Получаем введённый текст и пытаемся преобразовать в число
        carbs_input = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число граммов углеводов.")
        return DOSE_CARBS

    user_id = update.effective_user.id
    session = SessionLocal()

    # Сценарий: ввод после фото
    if context.user_data.pop('awaiting_carbs_after_photo', False):
        sugar     = context.user_data.pop('sugar')
        photo_path = context.user_data.pop('photo_path', None)
        xe        = context.user_data.pop('xe', None)

        profile = session.get(Profile, user_id)
        if not profile:
            session.close()
            await update.message.reply_text("Профиль не найден. Используйте /profile.", reply_markup=menu_keyboard)
            return ConversationHandler.END

        dose = calc_bolus(carbs_input, sugar,
                          PatientProfile(profile.icr, profile.cf, profile.target_bg))

        entry = Entry(
            telegram_id   = user_id,
            photo_path    = photo_path,
            carbs_g       = carbs_input,
            xe            = xe,
            sugar_before  = sugar,
            dose          = dose
        )
        session.add(entry)
        session.commit()
        session.close()

        await update.message.reply_text(
            f"💉 Рассчитанная доза: {dose} Ед\n"
            f"(углеводы: {carbs_input} г, сахар: {sugar} ммоль/л)",
            reply_markup=menu_keyboard
        )
        return ConversationHandler.END

    # Обычный сценарий /dose: углеводы после ввода сахара
    sugar = context.user_data.get('sugar')
    if sugar is None:
        session.close()
        await update.message.reply_text(
            "Сначала введите уровень сахара командой /dose или кнопкой «💉 Доза инсулина».",
            reply_markup=menu_keyboard
        )
        return ConversationHandler.END

    profile = session.get(Profile, user_id)
    if not profile:
        session.close()
        await update.message.reply_text("Профиль не найден. Используйте /profile.", reply_markup=menu_keyboard)
        return ConversationHandler.END

    dose = calc_bolus(carbs_input, sugar,
                      PatientProfile(profile.icr, profile.cf, profile.target_bg))

    entry = Entry(
        telegram_id  = user_id,
        sugar_before = sugar,
        carbs_g      = carbs_input,
        dose         = dose
    )
    session.add(entry)
    session.commit()
    session.close()

    await update.message.reply_text(
        f"💉 Рассчитанная доза: {dose} Ед\n"
        f"(углеводы: {carbs_input} г, сахар: {sugar} ммоль/л)",
        reply_markup=menu_keyboard
    )
    return ConversationHandler.END

async def dose_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=menu_keyboard)
    return ConversationHandler.END

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
    Загружает фото, отправляет его в Assistant API,
    ждёт текстовый ответ (GPT-4o), извлекает углеводы/ХЕ
    и переводит пользователя к вводу сахара.
    """
    user_id = update.effective_user.id
    # Скачиваем фото
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    os.makedirs("photos", exist_ok=True)
    path = f"photos/{user_id}_{photo.file_unique_id}.jpg"
    await file.download_to_drive(path)

    # --- Формируем профиль пользователя ---
    session = SessionLocal()
    user = session.get(User, user_id)
    profile = session.get(Profile, user_id)
    session.close()

    profile_text = None
    if profile:
        profile_text = (
            f"Профиль пользователя:\n"
            f"- ИКХ: {profile.icr} г/ед\n"
            f"- КЧ: {profile.cf} ммоль/л\n"
            f"- Целевой сахар: {profile.target_bg} ммоль/л\n"
        )
        # sugar = context.user_data.get("sugar")
        # if sugar is not None:
        #     profile_text += f"- Текущий сахар: {sugar} ммоль/л\n"
    else:
        profile_text = "Профиль пользователя не найден."

    # --- Передаём и текст, и фото ---
    run = send_message(user.thread_id, content=profile_text, image_path=path)

    await update.message.reply_text(
        "Фото отправлено, подождите ответ ассистента...",
        reply_markup=menu_keyboard
    )

    # Ждём выполнения
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(thread_id=user.thread_id, run_id=run.id)
        await asyncio.sleep(1)

    # Получаем САМОЕ СВЕЖЕЕ сообщение
    msgs = client.beta.threads.messages.list(
        thread_id=user.thread_id,
        order="desc",
        limit=1
    ).data
    if not msgs:
        await update.message.reply_text("❗ Нет ответа от ассистента.", reply_markup=menu_keyboard)
        return ConversationHandler.END

    last = msgs[0]  # самое новое сообщение
    blocks = getattr(last, "content", [])
    response_text = None
    for blk in blocks:
        txt = getattr(blk, "text", None)
        if txt:
            response_text = txt.value
            break

    logging.info(f"user_id={user_id} response_text={response_text}")

    if not response_text:
        await update.message.reply_text(
            "Ассистент прислал не-текстовый ответ. Попробуйте ещё раз.",
            reply_markup=menu_keyboard
        )
        return ConversationHandler.END

    # --- ВСЕГДА выводим ответ ассистента в чат ---
    await update.message.reply_text(response_text, reply_markup=menu_keyboard)

    # После получения response_text:
    if len(response_text.strip()) < 30 or response_text.strip().lower() in ["📷 фото еды", "что изображено на фото?", "пожалуйста, отправьте фото блюда — я помогу оценить углеводы и хлебные единицы (хе), а также рассчитать дозу инсулина, если известен ваш профиль и уровень сахара."]:
        await update.message.reply_text(
            "Ассистент не смог распознать блюдо. Попробуйте отправить другое фото или введите данные вручную.",
            reply_markup=menu_keyboard
        )
        context.user_data[WAITING_GPT_FLAG] = False
        return ConversationHandler.END

    # 5) Распознаём углеводы и ХЕ
    carbs, xe = extract_nutrition_info(response_text)
    # Сохраняем для следующего шага
    context.user_data["last_carbs"]      = carbs
    context.user_data["last_xe"]         = xe
    context.user_data["last_photo_time"] = time.time()
    context.user_data["photo_path"]      = path
    context.user_data["carbs"]           = carbs
    context.user_data["xe"]              = xe

    # 6) Проверяем наличие профиля
    session = SessionLocal()
    user_id = update.effective_user.id
    profile = session.get(Profile, user_id)
    session.close()

    # Если профиль есть, не пересылаем фразу GPT про ввод профиля, а сразу считаем дозу
    if profile and carbs is not None:
        sugar = context.user_data.get('sugar')
        if sugar is not None:
            dose = calc_bolus(carbs, sugar, PatientProfile(profile.icr, profile.cf, profile.target_bg))
            entry = Entry(
                telegram_id=user_id,
                photo_path=path,
                carbs_g=carbs,
                xe=xe,
                sugar_before=sugar,
                dose=dose
            )
            session = SessionLocal()
            session.add(entry)
            session.commit()
            session.close()
            await update.message.reply_text(
                f"💉 Ваша доза инсулина: {dose} Ед\n"
                f"(углеводы: {carbs} г, сахар: {sugar} ммоль/л)",
                reply_markup=menu_keyboard
            )
            return ConversationHandler.END
        else:
            # Если сахара нет, просим ввести сахар
            await update.message.reply_text(
                "Теперь введите текущий уровень сахара (ммоль/л):",
                reply_markup=menu_keyboard
            )
            return PHOTO_SUGAR
    else:
        # Если профиля нет, просим ввести сахар
        await update.message.reply_text(
            "Теперь введите текущий уровень сахара (ммоль/л):",
            reply_markup=menu_keyboard
        )
        return PHOTO_SUGAR

    context.user_data[WAITING_GPT_FLAG] = False

    # В photo_handler после получения response_text:
    logging.info(f"user_id={user_id} response={response_text}")

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

    # 6) Сохраняем запись
    entry = Entry(
        telegram_id   = user_id,
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
    context.user_data.clear()
    session = SessionLocal()
    user_id = update.effective_user.id
    entries = session.query(Entry).filter_by(telegram_id=user_id).order_by(Entry.timestamp.desc()).limit(5).all()
    session.close()
    if not entries:
        await update.message.reply_text("История пуста.")
        return
    text = "Последние записи:\n"
    for e in entries:
        text += f"\n{e.timestamp.strftime('%d.%m %H:%M')} — Сахар: {e.sugar_before or '-'} ммоль/л, Углеводы: {e.carbs_g or '-'} г, Доза: {e.dose or '-'} Ед"
    await update.message.reply_text(text)

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
    entry_points=[MessageHandler(filters.PHOTO, photo_handler)],
    states={
        PHOTO_SUGAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, photo_sugar_handler)],
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
    fallbacks=[CommandHandler("cancel", dose_cancel)],
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
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_with_gpt))
    app.run_polling()

if __name__ == "__main__":
    main()
