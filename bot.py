# bot.py
import os
import re
import asyncio
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
PROFILE_ICR, PROFILE_CF, PROFILE_TARGET = range(3)
DOSE_SUGAR, DOSE_CARBS = range(2)

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📷 Фото еды"), KeyboardButton("🍽️ Углеводы и сахар")],
        [KeyboardButton("💉 Доза инсулина"), KeyboardButton("📊 История")],
        [KeyboardButton("📄 Мой профиль"), KeyboardButton("🔄 Изменить профиль")],
        [KeyboardButton("🔁 Сброс")]
    ],
    resize_keyboard=True
)



def extract_nutrition_info(text: str):
    carbs = None
    xe = None
    match_carbs = re.search(r"(\d+[.,]?\d*)\s*(г|грамм[аов]?)\s*(углеводов|carbs)", text, re.IGNORECASE)
    match_xe = re.search(r"(\d+[.,]?\d*)\s*(ХЕ|XE|хлебных ед[иеиц])", text, re.IGNORECASE)
    if match_carbs:
        carbs = float(match_carbs.group(1).replace(",", "."))
    if match_xe:
        xe = float(match_xe.group(1).replace(",", "."))
    return carbs, xe

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text("Выберите действие:", reply_markup=menu_keyboard)

async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text("Введите текущий сахар (ммоль/л):")
    return DOSE_SUGAR

async def dose_sugar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['sugar'] = float(update.message.text)
        await update.message.reply_text("Введите углеводы (г):")
        return DOSE_CARBS
    except ValueError:
        await update.message.reply_text("Введите число.")
        return DOSE_SUGAR

async def dose_carbs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        carbs = float(update.message.text)
        sugar = context.user_data['sugar']
        session = SessionLocal()
        user_id = update.effective_user.id
        profile = session.get(Profile, user_id)
        if not profile:
            await update.message.reply_text("Профиль не найден. Используйте /profile.")
            return ConversationHandler.END
        dose = calc_bolus(carbs, sugar, PatientProfile(profile.icr, profile.cf, profile.target_bg))
        entry = Entry(telegram_id=user_id, sugar_before=sugar, carbs_g=carbs, dose=dose)
        session.add(entry)
        session.commit()
        session.close()
        await update.message.reply_text(f"Рассчитанная доза: {dose} Ед", reply_markup=menu_keyboard)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Введите число.")
        return DOSE_CARBS

async def dose_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=menu_keyboard)
    return ConversationHandler.END

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    os.makedirs("photos", exist_ok=True)
    path = f"photos/{user_id}_{photo.file_unique_id}.jpg"
    await file.download_to_drive(path)
    session = SessionLocal()
    user = session.get(User, user_id)
    run = send_message(user.thread_id, image_path=path)
    await update.message.reply_text("Фото отправлено, ожидайте ответ...")
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(thread_id=user.thread_id, run_id=run.id)
        await asyncio.sleep(2)
    messages = client.beta.threads.messages.list(thread_id=user.thread_id)
    response_text = messages.data[0].content[0].text.value
    carbs, xe = extract_nutrition_info(response_text)
    entry = Entry(telegram_id=user_id, photo_path=path, gpt_summary=response_text, carbs_g=carbs, xe=xe)
    session.add(entry)
    session.commit()
    session.close()
    result = f"Ответ GPT: {response_text}"
    if carbs or xe:
        result += f"\n\nРаспознано: {carbs or '-'} г углеводов, {xe or '-'} ХЕ"
    await update.message.reply_text(result)

async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    profile_conv = ConversationHandler(
        entry_points=[CommandHandler("profile", profile_start), MessageHandler(filters.Regex("^🔄 Изменить профиль$"), profile_start)],
        states={
            PROFILE_ICR: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_icr)],
            PROFILE_CF: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_cf)],
            PROFILE_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_target)],
        },
        fallbacks=[CommandHandler("cancel", profile_cancel)],
    )

    dose_conv = ConversationHandler(
        entry_points=[
            CommandHandler("dose", dose_start),
            MessageHandler(filters.Regex("^🍽️ Углеводы и сахар$"), dose_start)
        ],

        states={
            DOSE_SUGAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, dose_sugar)],
            DOSE_CARBS: [MessageHandler(filters.TEXT & ~filters.COMMAND, dose_carbs)],
        },
        fallbacks=[CommandHandler("cancel", dose_cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(CommandHandler("reset", reset_handler))
    app.add_handler(CommandHandler("history", history_handler))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(MessageHandler(filters.Regex("^📄 Мой профиль$"), profile_view))

    app.add_handler(profile_conv)
    app.add_handler(dose_conv)
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_with_gpt))
    app.run_polling()

if __name__ == "__main__":
    main()
