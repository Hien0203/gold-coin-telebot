# app.py - ĐÃ SỬA HOÀN CHỈNH
import os
import logging
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
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

telegram_app = ApplicationBuilder().token(TOKEN).build()
URL_VANG = "https://btmc.vn/"
URL_BINANCE = "https://api.binance.com/api/v3/ticker/price?symbol="

scheduler = BackgroundScheduler()
scheduler.start()

_main_loop = None
_app_initialized = False

def lay_gia_vang():
    try:
        res = requests.get(URL_VANG, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if res.status_code != 200:
            return "Warning: Trang BTMC đang bảo trì."
        soup = BeautifulSoup(res.text, "html.parser")
        bang = soup.find("table", class_=lambda x: x and "price" in x.lower())
        if not bang:
            return "Warning: Không tìm thấy bảng giá vàng."
        rows = bang.find_all("tr")[1:]
        result = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                loai = cols[1].get_text(" ", strip=True)
                mua = cols[3].get_text(" ", strip=True).replace(",", ".")
                ban = cols[4].get_text(" ", strip=True).replace(",", ".")
                result.append(f"{loai}\nMua: {mua or '–'} | Bán: {ban or '–'}")
        return "GIÁ VÀNG BTMC\n" + "\n\n".join(result)
    except Exception as e:
        logger.error(f"Lỗi lấy vàng: {e}")
        return "Warning: Không thể lấy giá vàng."

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

async def gia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = lay_gia_vang()
        logger.info(f"Gửi /gia: {len(msg)} ký tự")
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Lỗi gửi /gia: {e}")
        await update.message.reply_text("Lỗi: Không thể lấy giá vàng.")

async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = lay_gia_coin()
        logger.info(f"Gửi /coin: {len(msg)} ký tự")
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Lỗi gửi /coin: {e}")
        await update.message.reply_text("Lỗi: Không thể lấy giá coin.")

async def gui_gia_vang_tu_dong():
    try:
        await telegram_app.bot.send_message(chat_id=CHAT_ID, text=lay_gia_vang())
    except Exception as e:
        logger.error(f"Lỗi tự động: {e}")

async def initialize_telegram_app():
    global _app_initialized, _main_loop
    if not _app_initialized:
        await telegram_app.initialize()
        await telegram_app.start()
        _main_loop = asyncio.get_running_loop()
        _app_initialized = True

async def _process_update(data):
    try:
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Lỗi xử lý: {e}")

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        logger.info(f"Nhận: {data.get('message', {}).get('text')}")
        if _main_loop:
            asyncio.run_coroutine_threadsafe(_process_update(data), _main_loop)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook lỗi: {e}")
        return "Error", 500
# === THÊM LỆNH /test ===
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Gửi lệnh /test")
    await update.message.reply_text("Bot hoạt động 100%! Webhook OK!")


@app.route("/", methods=["GET"])
def index():
    return "Bot live!"

async def setup_bot_async():
    await initialize_telegram_app()
    await telegram_app.bot.delete_webhook(drop_pending_updates=True)
    await telegram_app.bot.set_webhook(url=f"{DOMAIN}/{TOKEN}")
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(gui_gia_vang_tu_dong(), _main_loop),
        "cron", hour=8, minute=0, timezone="Asia/Ho_Chi_Minh"
    )

telegram_app.add_handler(CommandHandler("gia", gia))
telegram_app.add_handler(CommandHandler("coin", coin))
telegram_app.add_handler(CommandHandler("test", test))

threading.Thread(target=lambda: asyncio.run(setup_bot_async()), daemon=True).start()
