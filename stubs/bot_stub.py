import re

PHOTO_SUGAR = 7
WAITING_GPT_FLAG = "waiting_gpt_response"

def extract_nutrition_info(text: str):
    carbs = xe = None
    m = re.search(r"углевод[^\d]*:\s*([\d.,]+)\s*г", text, re.IGNORECASE)
    if m:
        carbs = float(m.group(1).replace(",", "."))

    m = re.search(r"\bх[еe][^\d]*:\s*([\d.,]+)", text, re.IGNORECASE)
    if m:
        xe = float(m.group(1).replace(",", "."))

    if carbs is None:
        rng = re.search(r"(\d+[.,]?\d*)\s*[–-]\s*(\d+[.,]?\d*)\s*г", text, re.IGNORECASE)
        if rng:
            carbs = (float(rng.group(1).replace(",", ".")) + float(rng.group(2).replace(",", "."))) / 2

    if xe is None:
        rng = re.search(r"(\d+[.,]?\d*)\s*[–-]\s*(\d+[.,]?\d*)\s*(?:ХЕ|XE)", text, re.IGNORECASE)
        if rng:
            xe = (float(rng.group(1).replace(",", ".")) + float(rng.group(2).replace(",", "."))) / 2

    return carbs, xe

async def photo_handler(update, context, demo: bool = False):
    # simplified mock flow
    context.user_data[WAITING_GPT_FLAG] = True
    await update.message.reply_text("🔍 Анализирую фото (это займёт 5‑10 с)…")
    await update.message.reply_text("🍽️ На фото:\nУглеводы: 10 г\n\nВведите текущий сахар (ммоль/л) — и я рассчитаю дозу инсулина.")
    context.user_data.pop(WAITING_GPT_FLAG, None)
    return PHOTO_SUGAR

