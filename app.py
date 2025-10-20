# app.py - HOÀN CHỈNH, TỰ GỌI HANDLER
import os
import logging
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Update
from telegram.ext import ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import nest_asyncio
import datetime
import threading

nest_asyncio.apply()

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
DOMAIN = os.getenv("RENDER_EXTERNAL_URL")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URL_VANG = "https://btmc.vn"
URL_BINANCE = "https://api.binance.com/api/v3/ticker/price?symbol="

scheduler = BackgroundScheduler()
scheduler.start()

_main_loop = None
_bot = None

def lay_gia_vang():
    try:
        res = requests.get(URL_VANG, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        bang = soup.find("table", {"class": "table-price"})
        if not bang:
            return "Không tìm thấy bảng giá vàng."
        rows = bang.find_all("tr")[1:]
        result = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 4:
                loai = cols[0].get_text(strip=True)
                mua = cols[1].get_text(strip=True).replace(",", ".")
                ban = cols[2].get_text(strip=True).replace(",", ".")
                result.append(f"{loai}\nMua: {mua} | Bán: {ban}")
        return "GIÁ VÀNG BTMC\n" + "\n\n".join(result)
    except Exception as e:
        logger.error(f"Lỗi vàng: {e}")
        return "Không thể lấy giá vàng."

def lay_gia_coin():
    symbols = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
    msg = "GIÁ COIN (Test)\n\n"
    for name, sym in symbols.items():
        try:
            res = requests.get(URL_BINANCE + sym, timeout=5)
            data = res.json()
            price = float(data["price"])
            msg += f"{name}: {price:,.2f} USDT\n"
        except:
            msg += f"{name}: Lỗi\n"
    return msg

async def test(update: Update, context):
    try:
        logger.info("Gửi /test")
        await update.message.reply_text("Bot hoạt động 100%! Webhook OK!")
    except Exception as e:
        logger.error(f"Lỗi /test: {e}")

async def gia(update: Update, context):
    try:
        msg = lay_gia_vang()
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Lỗi /gia: {e}")
        await update.message.reply_text("Lỗi hệ thống.")

async def coin(update: Update, context):
    try:
        msg = lay_gia_coin()
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Lỗi /coin: {e}")
        await update.message.reply_text("Lỗi hệ thống.")

async def start(update: Update, context):
    await update.message.reply_text("Chào mừng! Dùng /test, /gia, /coin")

async def gui_gia_vang_tu_dong():
    try:
        await _bot.send_message(chat_id=CHAT_ID, text=lay_gia_vang())
    except Exception as e:
        logger.error(f"Lỗi tự động: {e}")

async def setup_bot_async():
    global _main_loop, _bot
    from telegram.ext import ApplicationBuilder
    app = ApplicationBuilder().token(TOKEN).build()
    await app.initialize()
    await app.start()
    _bot = app.bot
    _main_loop = asyncio.get_running_loop()
    
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.bot.set_webhook(url=f"{DOMAIN}/{TOKEN}")
    
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(gui_gia_vang_tu_dong(), _main_loop),
        "cron", hour=8, minute=0, timezone="Asia/Ho_Chi_Minh"
    )

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, _bot)
        text = update.message.text.strip().lower() if update.message else ""
        logger.info(f"Nhận: {text}")
        
        if text == "/test":
            asyncio.run_coroutine_threadsafe(test(update, None), _main_loop)
        elif text == "/gia":
            asyncio.run_coroutine_threadsafe(gia(update, None), _main_loop)
        elif text == "/coin":
            asyncio.run_coroutine_threadsafe(coin(update, None), _main_loop)
        elif text == "/start":
            asyncio.run_coroutine_threadsafe(start(update, None), _main_loop)
        
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook lỗi: {e}")
        return "Error", 500

@app.route("/", methods=["GET"])
def index():
    return "Bot live!"

threading.Thread(target=lambda: asyncio.run(setup_bot_async()), daemon=True).start()