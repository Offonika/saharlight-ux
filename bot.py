# bot.py
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from db import SessionLocal, init_db, User, Profile, Entry
from gpt_client import create_thread, send_message, client
from functions import PatientProfile, calc_bolus
from config import TELEGRAM_TOKEN, OPENAI_ASSISTANT_ID

init_db()

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📷 Фото еды"), KeyboardButton("🍽️ Углеводы и сахар")],
        [KeyboardButton("💉 Доза инсулина"), KeyboardButton("📊 История")],
        [KeyboardButton("⚙️ Профиль"), KeyboardButton("🔁 Сброс")]
    ],
    resize_keyboard=True
)

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

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Использование: /profile <ИКХ> <КЧ> <целевой сахар>")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    os.makedirs('photos', exist_ok=True)
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

    entry = Entry(telegram_id=user_id, photo_path=path, gpt_summary=response_text)
    session.add(entry)
    session.commit()
    session.close()

    await update.message.reply_text(f"Ответ GPT: {response_text}")

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
        row = f"\n{e.timestamp.strftime('%d.%m %H:%M')} — Сахар: {e.sugar_before or '-'} ммоль/л, Углеводы: {e.carbs_g or '-'} г, Доза: {e.dose or '-'} Ед"
        text += row

    await update.message.reply_text(text)

async def chat_with_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📷 Фото еды":
        await update.message.reply_text("Пожалуйста, отправьте фотографию еды.")
    elif text == "🍽️ Углеводы и сахар":
        await update.message.reply_text("Введите команду /dose <сахар> <углеводы в граммах>")
    elif text == "💉 Доза инсулина":
        await update.message.reply_text("Введите команду /dose <сахар> <углеводы в граммах>")
    elif text == "📊 История":
        await history_handler(update, context)
    elif text == "⚙️ Профиль":
        await profile_handler(update, context)
    elif text == "🔁 Сброс":
        await update.message.reply_text("Функция сброса профиля пока не реализована.")
    else:
        session = SessionLocal()
        user_id = update.effective_user.id
        user = session.get(User, user_id)
        session.close()

        if not user:
            await update.message.reply_text("Пожалуйста, начните с команды /start.")
            return

        run = send_message(user.thread_id, content=text)
        await update.message.reply_text("Отправлено ассистенту, ждите ответа...")

        while run.status in ["queued", "in_progress"]:
            run = client.beta.threads.runs.retrieve(thread_id=user.thread_id, run_id=run.id)
            await asyncio.sleep(2)

        messages = client.beta.threads.messages.list(thread_id=user.thread_id)
        response = messages.data[0].content[0].text.value

        await update.message.reply_text(response)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_with_gpt))
    app.run_polling()

if __name__ == "__main__":
    main()

