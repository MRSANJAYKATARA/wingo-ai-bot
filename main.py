import os
import time
import json
import random
import asyncio
import signal
from collections import deque
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# Telegram bot credentials
TOKEN = "7963409762:AAEEw4ctYgqY3iNtVbuq44Swdncm6bu7BwY"
CHANNEL_ID = "@whitehackerai"

# Bot state variables
latest_period = None
wins = 0
losses = 0
current_prediction = {}
last_result = "WAITING..."
data_history = deque(maxlen=10)
awaiting_period = False
awaiting_results = False

# Shutdown handler for clean exit
signal.signal(signal.SIGINT, lambda sig, frame: exit())
signal.signal(signal.SIGTERM, lambda sig, frame: exit())

# Load stored stats from file
def load_stats():
    global wins, losses
    if os.path.exists("wingo_stats.json"):
        with open("wingo_stats.json") as f:
            stats = json.load(f)
            wins = stats.get("wins", 0)
            losses = stats.get("losses", 0)

# Save current stats to file
def save_stats():
    with open("wingo_stats.json", 'w') as f:
        json.dump({"wins": wins, "losses": losses}, f)

# Determine color based on number
def get_color(num):
    if num in [0, 5]: return "🟣 VIOLET"
    return "🔴 RED" if num % 2 == 0 else "🟢 GREEN"

# Determine size based on number
def get_size(num):
    return "BIG" if num >= 5 else "SMALL"

# Predict next number using recent history
def predict_ai():
    if len(data_history) < 3:
        pred_num = random.randint(0, 9)
    else:
        last_three = list(data_history)[-3:]
        avg = sum(last_three) / len(last_three)
        if avg < 3.5:
            pred_num = random.choices([6, 7, 8, 9], weights=[25, 30, 25, 20])[0]
        elif avg > 6.5:
            pred_num = random.choices([0, 1, 2, 3], weights=[20, 25, 30, 25])[0]
        else:
            pred_num = random.randint(0, 9)
    return pred_num, get_color(pred_num), get_size(pred_num)

# Generate inline menu UI
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ START PREDICTION", callback_data="start_prediction")],
        [InlineKeyboardButton("2️⃣ REGISTER & SUPPORT", callback_data="support_menu")],
        [InlineKeyboardButton("3️⃣ RESULT & STATS", callback_data="show_stats")],
        [InlineKeyboardButton("4️⃣ NEXT PREDICTION", callback_data="next_prediction")]
    ])

# Generate support menu UI
def support_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 REGISTER NOW", url="https://51game6.in/#/register?invitationCode=53383112465")],
        [InlineKeyboardButton("👑 VIP SUPPORT", url="https://t.me/x1nonly_white_aura")]
    ])

# Create styled prediction message
def format_prediction_message(period):
    global current_prediction
    if not current_prediction:
        current_prediction['number'], current_prediction['color'], current_prediction['size'] = predict_ai()
    pred_num = current_prediction['number']
    pred_color = current_prediction['color']
    pred_size = current_prediction['size']
    accuracy = round((wins / (wins + losses)) * 100, 1) if (wins + losses) > 0 else 0.0
    msg = (
        "🔥 51Game  AI BOT  \n"
        "✨• PREDICTION 💎✨  \n\n"
        f"🧣 PERIOD NUMBER ➔ {period[-3:] if period else '---'}  \n"
        f"🎯 BET ➔ {pred_num} {pred_size} {pred_color.split()[0]}  \n\n"
        f"🖙 LAST RESULT ➔ {last_result}  \n"
        f"📊 WIN: {wins}   |   LOSS: {losses}    R - [click  here](https://t.me/x1nonly_white_aura)"
    )
    return msg

# Handle user messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global latest_period, awaiting_period, awaiting_results, data_history, current_prediction, wins, losses, last_result
    text = update.message.text.strip()
    if awaiting_period:
        latest_period = text
        awaiting_period = False
        await update.message.reply_text("✅ Period saved. Now enter last 3 results (space-separated):")
        awaiting_results = True
        return
    elif awaiting_results:
        try:
            nums = list(map(int, text.split()))
            if len(nums) != 3:
                await update.message.reply_text("❌ Enter exactly 3 numbers separated by space.")
                return
            data_history.extend(nums)
            actual_size = get_size(nums[-1])
            if actual_size == current_prediction.get('size'):
                last_result = f"✅ {actual_size} WIN"
                wins += 1
            else:
                last_result = "❌ LOSS"
                losses += 1
            save_stats()
            current_prediction['number'], current_prediction['color'], current_prediction['size'] = predict_ai()
            awaiting_results = False
            await update.message.reply_text(format_prediction_message(latest_period), parse_mode="Markdown")
        except:
            await update.message.reply_text("❌ Invalid input. Send 3 numbers only.")
        return

# Handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to 51 Game AI Bot!\nSelect an option below:",
        reply_markup=main_menu()
    )

# Handle button clicks
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global awaiting_period, awaiting_results
    query = update.callback_query
    await query.answer()
    if query.data == "start_prediction":
        awaiting_period = True
        awaiting_results = False
        await query.edit_message_text("🔢 Send the current period number:")
    elif query.data == "next_prediction":
        awaiting_results = True
        await query.edit_message_text("🔢 Send last 3 result numbers (space-separated):")
    elif query.data == "support_menu":
        await query.edit_message_text("👇 Links:", reply_markup=support_menu())
    elif query.data == "show_stats":
        await query.edit_message_text(f"📊 STATS ➔ ✅ W: {wins} | ❌ L: {losses}")

# Bot main function
def main():
    load_stats()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ BOT RUNNING")
    app.run_polling()

# Entry point
if __name__ == "__main__":
    main()
    
