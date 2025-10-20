# app.py
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

# ===============================================================
# CẤU HÌNH
# ===============================================================
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
DOMAIN = os.getenv("RENDER_EXTERNAL_URL")

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

telegram_app = ApplicationBuilder().token(TOKEN).build()

URL_VANG = "https://btmc.vn/trang-vang"
URL_BINANCE = "https://api.binance.com/api/v3/ticker/price?symbol="

scheduler = BackgroundScheduler()
scheduler.start()

_main_loop = None
_app_initialized = False

# ===============================================================
# LẤY DỮ LIỆU
# ===============================================================
def lay_gia_vang():
    try:
        res = requests.get(URL_VANG, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        bang = soup.find("table", {"class": "bd_price_home"})
        if not bang: return "Không tìm thấy bảng giá vàng."
        rows = bang.find_all("tr")[1:]
        result = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                loai = cols[1].get_text(" ", strip=True)
                mua = cols[3].get_text(" ", strip=True).replace(",", ".")
                ban = cols[4].get_text(" ", strip=True).replace(",", ".")
                result.append(f"{loai}\nMua: {mua or '–'} | Bán: {ban or '–'}")
        note = soup.find("p", class_="note")
        capnhat = note.get_text(strip=True).replace("Nguồn: www.btmc.vn", "").strip() if note else ""
        return f"GIÁ VÀNG BẢO TÍN MINH CHÂU\n{capnhat}\n\n" + "\n\n".join(result)
    except Exception as e:
        return f"Lỗi: {e}"

def lay_gia_coin():
    symbols = {"AVNT": "AVNTUSDT", "TREE": "TREEUSDT", "ASTER": "ASTERUSDT", "SOMI": "SOMIUSDT"}
    msg = "GIÁ COIN (Binance)\n\n"
    for name, sym in symbols.items():
        try:
            res = requests.get(URL_BINANCE + sym, timeout=5)
            price = float(res.json()["price"])
            msg += f"{name}: {price:,.4f} USDT\n"
        except:
            msg += f"{name}: Lỗi\n"
    return msg.strip()

# ===============================================================
# LỆNH
# ===============================================================
async def gia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(lay_gia_vang())

async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(lay_gia_coin())

async def gui_gia_vang_tu_dong():
    try:
        text = f"Cập nhật giá vàng {datetime.datetime.now():%d/%m/%Y %H:%M}\n\n{lay_gia_vang()}"
        await telegram_app.bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        logger.error(f"Lỗi gửi tự động: {e}")

# ===============================================================
# KHỞI TẠO
# ===============================================================
async def initialize_telegram_app():
    global _app_initialized, _main_loop
    if not _app_initialized:
        await telegram_app.initialize()
        await telegram_app.start()
        _main_loop = asyncio.get_running_loop()
        _app_initialized = True

async def _process_update(data):
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)

# ===============================================================
# WEBHOOK
# ===============================================================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        logger.info(f"Nhận lệnh: {data.get('message', {}).get('text')}")
        if _main_loop:
            asyncio.run_coroutine_threadsafe(_process_update(data), _main_loop)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook lỗi: {e}")
        return "Error", 500

@app.route("/", methods=["GET"])
def index():
    return "Bot đang chạy với Gunicorn!", 200

# ===============================================================
# SETUP BOT
# ===============================================================
async def setup_bot_async():
    await initialize_telegram_app()
    await telegram_app.bot.delete_webhook(drop_pending_updates=True)
    webhook_url = f"{DOMAIN}/{TOKEN}"
    await telegram_app.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook: {webhook_url}")

    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(gui_gia_vang_tu_dong(), _main_loop),
        "cron", hour=8, minute=0, timezone="Asia/Ho_Chi_Minh"
    )

# ===============================================================
# CHẠY KHI KHỞI ĐỘNG (GUNICORN)
# ===============================================================
telegram_app.add_handler(CommandHandler("gia", gia))
telegram_app.add_handler(CommandHandler("coin", coin))

# Chạy setup bot trong thread
threading.Thread(target=lambda: asyncio.run(setup_bot_async()), daemon=True).start()