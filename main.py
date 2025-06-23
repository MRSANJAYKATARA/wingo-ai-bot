
import os
import time
import json
import random
import asyncio
import signal
from datetime import datetime
from collections import deque
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    JobQueue
)

# ====== CONFIG ======
TOKEN = "7713466266:AAGopg4ItYBXvJxb7Ic6cw5_3HxskjCEepI"
CHANNEL_ID = "@whitehackerai"
CHROMEDRIVER_PATH = "/data/data/com.termux/files/usr/lib/chromium/chromedriver"
CHROMIUM_BINARY = "/data/data/com.termux/files/usr/lib/chromium/chrome"
WINGO_URL = "https://zdj6.wingoanalyst.com/#/wingo_1m"
DATA_FILE = "wingo_stats.json"

# ====== VARIABLES ======
latest_period = None
wins = 0
losses = 0
current_prediction = {}
last_result = "WAITING..."
data_history = deque(maxlen=10)
driver = None
running = True

# ====== EXIT HANDLER ======
def signal_handler(sig, frame):
    os.system("clear")
    print("SUCCESSFULLY EXITED BY USER ✅")
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ====== FILE I/O ======
def load_stats():
    global wins, losses
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE) as f:
                stats = json.load(f)
                wins = stats.get("wins", 0)
                losses = stats.get("losses", 0)
    except: pass

def save_stats():
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump({"wins": wins, "losses": losses}, f)
    except: pass

# ====== SELENIUM ======
def start_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.binary_location = CHROMIUM_BINARY
    service = Service(executable_path=CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)

def fetch_live():
    global driver
    try:
        if not driver:
            driver = start_driver()
        driver.get(WINGO_URL)
        time.sleep(3)
        period_elem = driver.find_elements(By.XPATH, "//span[contains(text(),'202')]")
        period = period_elem[0].text.strip() if period_elem else "UNKNOWN"
        num_elem = driver.find_elements(By.XPATH, "//div[@style[contains(.,'height: 50px')]]/span")
        current_number = int(num_elem[0].text.strip()) if num_elem else -1
        return period, current_number
    except:
        try:
            if driver:
                driver.quit()
        except: pass
        driver = None
        return "ERROR", -1

# ====== AI LOGIC ======
def get_color(num):
    if num in [0, 5]: return "🟣 VIOLET"
    return "🔴 RED" if num % 2 == 0 else "🟢 GREEN"

def get_size(num):
    return "BIG" if num >= 5 else "SMALL"

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

# ====== UI & BUTTONS ======
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ START PREDICTION", callback_data="start_prediction")],
        [InlineKeyboardButton("2️⃣ REGISTER & SUPPORT", callback_data="support_menu")],
        [InlineKeyboardButton("3️⃣ RESULT & STATS", callback_data="show_stats")]
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
        "🔥 51Game  AI BOT  \n"
        "✨• PREDICTION 💎✨  \n\n"
        f"🧿 PERIOD NUMBER ➤ {period[-3:] if period else '---'}  \n"
        f"🎯 BET ➤ {pred_num} {pred_size} {pred_color.split()[0]}  \n\n"
        f"🔙 LAST RESULT ➤ {last_result}  \n"
        f"📊 WIN: {wins}   |   LOSS: {losses}    R - [click  here](https://t.me/x1nonly_white_aura)"
    )
    return msg

# ====== LOOP ======
async def prediction_loop(context: ContextTypes.DEFAULT_TYPE):
    global latest_period, wins, losses, current_prediction, last_result, data_history
    while True:
        period, current_number = fetch_live()
        if period == "ERROR" or current_number == -1:
            await asyncio.sleep(60)
            continue
        if period != latest_period:
            if latest_period and current_prediction:
                actual_size = get_size(current_number)
                if actual_size == current_prediction['size']:
                    last_result = f"✅ {actual_size} WIN"
                    wins += 1
                else:
                    last_result = "❌ LOSS"
                    losses += 1
                save_stats()
            data_history.append(current_number)
            latest_period = period
            current_prediction['number'], current_prediction['color'], current_prediction['size'] = predict_ai()
            try:
                await context.bot.send_message(chat_id=CHANNEL_ID, text=format_prediction_message(period), parse_mode="Markdown")
            except: pass
        await asyncio.sleep(60)

# ====== HANDLERS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "👋 Welcome to 51 Game AI Bot!\nSelect an option below:",
            reply_markup=main_menu()
        )
    except: pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        if query.data == "start_prediction":
            await query.edit_message_text(
                format_prediction_message(latest_period if latest_period else "---"),
                reply_markup=support_menu(),
                parse_mode="Markdown"
            )
        elif query.data == "support_menu":
            await query.edit_message_text("👇 Links:", reply_markup=support_menu())
        elif query.data == "show_stats":
            await query.edit_message_text(
                f"📊 STATS ➤ ✅ W: {wins} | ❌ L: {losses}")
    except: pass

# ====== MAIN FUNCTION ======
def main():
    global driver
    load_stats()
    try:
        driver = start_driver()
    except:
        driver = None

    app = Application.builder().token(TOKEN).build()

    # ✅ FIXED JOBQUEUE SETUP
    job_queue = JobQueue()
    job_queue.set_application(app)
    job_queue.start()
    app.job_queue = job_queue

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.job_queue.run_once(lambda ctx: asyncio.create_task(prediction_loop(ctx)), when=5)

    os.system("clear")
    print("SUCCESSFULLY BOT RUNNING ✅")
    try:
        app.run_polling()
    except: pass

if __name__ == "__main__":
    main()
