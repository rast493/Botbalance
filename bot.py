import logging
import json
import os
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ——— Настройки ———
BOT_TOKEN = "8755796189:AAHMgipOU_NToRmjrfypQGnaMA9Uelqq8qg"  # Вставь токен от @BotFather
DATA_FILE = "balances.json"

logging.basicConfig(level=logging.INFO)

# ——— Числовой паттерн ———
# Поддерживает: 100, 1.5, 1,5, 1 000, 1 000.5, 1_000 и т.д.
NUM = r"(\d[\d\s_]*(?:[.,]\d+)?)"

# ——— Работа с файлом данных ———
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_chat_balance(data, chat_id):
    key = str(chat_id)
    if key not in data:
        data[key] = {"г": 0.0, "п": 0.0}
    return data[key]

def parse_amount(raw: str) -> float:
    """Убирает пробелы и подчёркивания-разделители, меняет запятую на точку."""
    cleaned = raw.replace(" ", "").replace("_", "").replace(",", ".")
    return float(cleaned)

# ——— Обработчик сообщений ———
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    chat_id = update.message.chat_id

    data = load_data()
    balance = get_chat_balance(data, chat_id)

    # +бал <число> г|п  ИЛИ  +бал г|п <число>
    add_match = (
        re.match(rf"^\+бал\s+{NUM}\s*([гп])$", text, re.IGNORECASE) or
        re.match(rf"^\+бал\s+([гп])\s*{NUM}$", text, re.IGNORECASE)
    )
    if add_match:
        groups = add_match.groups()
        if re.match(r"^[гп]$", groups[0], re.IGNORECASE):
            currency, raw_amount = groups[0].lower(), groups[1]
        else:
            raw_amount, currency = groups[0], groups[1].lower()
        amount = parse_amount(raw_amount)
        balance[currency] = balance.get(currency, 0.0) + amount
        data[str(chat_id)] = balance
        save_data(data)
        await update.message.reply_text(
            f"✅ +{fmt(amount)} {currency} добавлено!\n"
            f"Итого {currency}: {fmt(balance[currency])}"
        )
        return

    # -бал <число> г|п  ИЛИ  -бал г|п <число>
    sub_match = (
        re.match(rf"^-бал\s+{NUM}\s*([гп])$", text, re.IGNORECASE) or
        re.match(rf"^-бал\s+([гп])\s*{NUM}$", text, re.IGNORECASE)
    )
    if sub_match:
        groups = sub_match.groups()
        if re.match(r"^[гп]$", groups[0], re.IGNORECASE):
            currency, raw_amount = groups[0].lower(), groups[1]
        else:
            raw_amount, currency = groups[0], groups[1].lower()
        amount = parse_amount(raw_amount)
        balance[currency] = balance.get(currency, 0.0) - amount
        data[str(chat_id)] = balance
        save_data(data)
        await update.message.reply_text(
            f"➖ -{fmt(amount)} {currency} снято!\n"
            f"Итого {currency}: {fmt(balance[currency])}"
        )
        return

    # бал г|п — показать один баланс
    single_match = re.match(r"^бал\s+([гп])$", text, re.IGNORECASE)
    if single_match:
        currency = single_match.group(1).lower()
        await update.message.reply_text(
            f"📊 Баланс {currency}: {fmt(balance.get(currency, 0.0))}"
        )
        return

    # бал — показать оба баланса
    if re.match(r"^бал$", text, re.IGNORECASE):
        await update.message.reply_text(
            f"📊 Балансы:\n"
            f"  г: {fmt(balance.get('г', 0.0))}\n"
            f"  п: {fmt(balance.get('п', 0.0))}"
        )
        return

def fmt(value: float) -> str:
    """Форматирует число красиво: без лишних нулей, с разделителем тысяч."""
    if value == int(value):
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")

# ——— Запуск ———
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    app.run_polling()
