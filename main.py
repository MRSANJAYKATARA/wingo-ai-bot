# Enhanced 51Game AI Bot with Selenium Integration
import os
import json
import random
import asyncio
import signal
from collections import deque
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# --- Configuration ---
TOKEN = "8040444270:AAGfxIY5ijJcvBVn530QHqgBSYSTWeOfCpY"
CHANNEL_ID = "@whitehackerai"
WINGO_URL = "https://zdj6.wingoanalyst.com/#/wingo_30s"

# --- Global Variables ---
latest_period = None
wins = 0
losses = 0
current_prediction = {}
last_result = "WAITING..."
data_history = deque(maxlen=10)
awaiting_period = False
awaiting_results = False

# --- Selenium Setup ---
def setup_browser():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=options)
    return driver

def run_prediction_selenium():
    driver = setup_browser()
    try:
        driver.get(WINGO_URL)
        print("🔍 Opened Wingo Analyst Site.")

        # Wait and fetch the latest period and result number
        driver.implicitly_wait(10)
        period_elements = driver.find_elements(By.XPATH, "//span[contains(text(),'202')]")
        number_elements = driver.find_elements(By.XPATH, "//div[@style[contains(.,'height: 50px')]]")

        period = period_elements[0].text.strip() if period_elements else "UNKNOWN"
        numbers = [int(el.text.strip()) for el in number_elements if el.text.strip().isdigit()]

        if numbers:
            data_history.append(numbers[0])
            print(f"✅ Selenium fetched: Period = {period}, Number = {numbers[0]}")
        else:
            print("⚠️ No valid number found.")

    except Exception as e:
        print(f"❌ Selenium error: {e}")
    finally:
        driver.quit()

# --- Stats Functions ---
def load_stats():
    global wins, losses
    if os.path.exists("wingo_stats.json"):
        with open("wingo_stats.json") as f:
            stats = json.load(f)
            wins = stats.get("wins", 0)
            losses = stats.get("losses", 0)

def save_stats():
    with open("wingo_stats.json", 'w') as f:
        json.dump({"wins": wins, "losses": losses}, f)

def get_color(num):
    if num in [0, 5]:
        return "🟣 VIOLET"
    return "🔴 RED" if num % 2 == 0 else "🟢 GREEN"

def get_size(num):
    return "BIG" if num >= 5 else "SMALL"

def predict_ai():
    if len(data_history) < 3:
        pred_num = random.randint(0, 9)
    else:
        last_three = list(data_history)[-3:]
        avg = sum(last_three) / 3
        if avg < 3.5:
            pred_num = random.choices([6, 7, 8, 9], weights=[25, 30, 25, 20])[0]
        elif avg > 6.5:
            pred_num = random.choices([0, 1, 2, 3], weights=[20, 25, 30, 25])[0]
        else:
            pred_num = random.randint(0, 9)
    return pred_num, get_color(pred_num), get_size(pred_num)

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ START PREDICTION", callback_data="start_prediction")],
        [InlineKeyboardButton("2️⃣ REGISTER & SUPPORT", callback_data="support_menu")],
        [InlineKeyboardButton("3️⃣ RESULT & STATS", callback_data="show_stats")],
        [InlineKeyboardButton("4️⃣ NEXT PREDICTION", callback_data="next_prediction")]
    ])

def support_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 REGISTER NOW", url="https://51game6.in/#/register?invitationCode=53383112465")],
        [InlineKeyboardButton("👑 VIP SUPPORT", url="https://t.me/x1nonly_white_aura")]
    ])

def format_prediction_message(period):
    global current_prediction
    if not current_prediction:
        current_prediction['number'], current_prediction['color'], current_prediction['size'] = predict_ai()

    pred_num = current_prediction['number']
    pred_color = current_prediction['color']
    pred_size = current_prediction['size']
    accuracy = round((wins / (wins + losses)) * 100, 1) if (wins + losses) > 0 else 0.0

    msg = (
        "🔥 51Game AI BOT\n"
        "✨• PREDICTION 💫✨\n\n"
        f"🧿 PERIOD NUMBER ➤ {period[-3:] if period else '---'}\n"
        f"🎯 BET ➤ {pred_num} {pred_size} {pred_color.split()[0]}\n\n"
        f"🔙 LAST RESULT ➤ {last_result}\n"
        f"📊 WIN: {wins}   |   LOSS: {losses}    R - [click here](https://t.me/x1nonly_white_aura)"
    )
    return msg

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global latest_period, awaiting_period, awaiting_results, data_history, current_prediction, wins, losses, last_result
    text = update.message.text.strip()

    if awaiting_period:
        latest_period = text
        awaiting_period = False
        awaiting_results = True
        await update.message.reply_text("✅ Period saved. Now enter last 3 results (space-separated):")
        return

    if awaiting_results:
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to 51 Game AI Bot!\nSelect an option below:",
        reply_markup=main_menu()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global awaiting_period, awaiting_results
    query = update.callback_query
    await query.answer()

    if query.data == "start_prediction":
        run_prediction_selenium()
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

def main():
    load_stats()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
    
