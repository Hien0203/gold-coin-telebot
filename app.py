# app.py - HOÀN CHỈNH, THÊM SHUTDOWN VÀ STABILITY
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
import time
import signal

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

URL_VANG = "https://btmc.vn/gia-vang"
URL_BINANCE = "https://api.binance.com/api/v3/ticker/price?symbol="

scheduler = BackgroundScheduler()
scheduler.start()

_main_loop = None
_bot = None
_is_ready = False

# ===============================================================
# SHUTDOWN HANDLER
# ===============================================================
def shutdown_handler(signum, frame):
    global _bot, _main_loop
    logger.info("Nhận signal shutdown...")
    if _bot:
        asyncio.run_coroutine_threadsafe(_bot.stop(), _main_loop)
    if _main_loop:
        _main_loop.close()
    scheduler.shutdown()
    logger.info("Shutdown hoàn tất!")
    exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

# ===============================================================
# LẤY DỮ LIỆU
# ===============================================================
def lay_gia_vang():
    try:
        res = requests.get(URL_VANG, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if res.status_code != 200:
            return "Trang BTMC đang bảo trì."
        soup = BeautifulSoup(res.text, "html.parser")
        bang = soup.find("table", {"class": "table-price"}) or soup.find("table")
        if not bang:
            return "Không tìm thấy bảng giá vàng."
        rows = bang.find_all("tr")[1:]
        result = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                loai = cols[0].get_text(strip=True)
                mua = cols[1].get_text(strip=True).replace(",", ".")
                ban = cols[2].get_text(strip=True).replace(",", ".")
                result.append(f"{loai}\nMua: {mua} | Bán: {ban}")
        return "GIÁ VÀNG BTMC\n" + "\n\n".join(result) if result else "Không có dữ liệu."
    except Exception as e:
        logger.error(f"Lỗi lấy vàng: {e}")
        return "Không thể lấy giá vàng."

def lay_gia_coin():
    symbols = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
    msg = "GIÁ COIN (Binance)\n\n"
    for name, sym in symbols.items():
        try:
            res = requests.get(URL_BINANCE + sym, timeout=5)
            data = res.json()
            price = float(data["price"])
            msg += f"{name}: {price:,.2f} USDT\n"
        except Exception as e:
            logger.error(f"Lỗi coin {name}: {e}")
            msg += f"{name}: Lỗi\n"
    return msg

# ===============================================================
# LỆNH
# ===============================================================
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
    await update.message.reply_text(
        "Chào mừng đến với Gold & Coin Bot!\n\n"
        "/test - Kiểm tra bot\n"
        "/gia - Giá vàng BTMC\n"
        "/coin - Giá BTC, ETH\n\n"
        "Cập nhật tự động 8h sáng."
    )

async def gui_gia_vang_tu_dong():
    try:
        await _bot.send_message(chat_id=CHAT_ID, text=lay_gia_vang())
        logger.info("Gửi giá vàng tự động thành công!")
    except Exception as e:
        logger.error(f"Lỗi tự động: {e}")

# ===============================================================
# KHỞI TẠO BOT
# ===============================================================
async def setup_bot_async():
    global _main_loop, _bot, _is_ready
    from telegram.ext import ApplicationBuilder
    application = ApplicationBuilder().token(TOKEN).build()
    await application.initialize()
    await application.start()
    _bot = application.bot
    _main_loop = asyncio.get_event_loop()
    if not _main_loop.is_running():
        asyncio.set_event_loop(_main_loop)
    
    await application.bot.delete_webhook(drop_pending_updates=True)
    webhook_url = f"{DOMAIN}/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook: {webhook_url}")
    
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(gui_gia_vang_tu_dong(), _main_loop),
        "cron", hour=8, minute=0, timezone="Asia/Ho_Chi_Minh"
    )
    logger.info("Đã lên lịch gửi tự động 8h sáng")
    _is_ready = True

# ===============================================================
# WEBHOOK – TỰ GỌI HANDLER
# ===============================================================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    global _main_loop, _bot, _is_ready
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, _bot)
        if not update.message or not update.message.text:
            return "OK", 200
        
        text = update.message.text.strip().lower()
        logger.info(f"Nhận lệnh: {text}")
        
        start_time = time.time()
        while not _is_ready and time.time() - start_time < 10:
            time.sleep(0.1)
        
        if not _is_ready or not _main_loop or not _bot:
            logger.error("Bot chưa sẵn sàng")
            return "Error: Bot initializing", 503
        
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
    return "Bot đang chạy! Dùng /test để kiểm tra.", 200

# ===============================================================
# KHỞI ĐỘNG
# ===============================================================
threading.Thread(target=lambda: [time.sleep(2), asyncio.run(setup_bot_async())], daemon=True).start()# app.py - HOÀN CHỈNH, THÊM SHUTDOWN VÀ STABILITY
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
import time
import signal

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

URL_VANG = "https://btmc.vn/gia-vang"
URL_BINANCE = "https://api.binance.com/api/v3/ticker/price?symbol="

scheduler = BackgroundScheduler()
scheduler.start()

_main_loop = None
_bot = None
_is_ready = False

# ===============================================================
# SHUTDOWN HANDLER
# ===============================================================
def shutdown_handler(signum, frame):
    global _bot, _main_loop
    logger.info("Nhận signal shutdown...")
    if _bot:
        asyncio.run_coroutine_threadsafe(_bot.stop(), _main_loop)
    if _main_loop:
        _main_loop.close()
    scheduler.shutdown()
    logger.info("Shutdown hoàn tất!")
    exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

# ===============================================================
# LẤY DỮ LIỆU
# ===============================================================
def lay_gia_vang():
    try:
        res = requests.get(URL_VANG, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if res.status_code != 200:
            return "Trang BTMC đang bảo trì."
        soup = BeautifulSoup(res.text, "html.parser")
        bang = soup.find("table", {"class": "table-price"}) or soup.find("table")
        if not bang:
            return "Không tìm thấy bảng giá vàng."
        rows = bang.find_all("tr")[1:]
        result = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                loai = cols[0].get_text(strip=True)
                mua = cols[1].get_text(strip=True).replace(",", ".")
                ban = cols[2].get_text(strip=True).replace(",", ".")
                result.append(f"{loai}\nMua: {mua} | Bán: {ban}")
        return "GIÁ VÀNG BTMC\n" + "\n\n".join(result) if result else "Không có dữ liệu."
    except Exception as e:
        logger.error(f"Lỗi lấy vàng: {e}")
        return "Không thể lấy giá vàng."

def lay_gia_coin():
    symbols = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
    msg = "GIÁ COIN (Binance)\n\n"
    for name, sym in symbols.items():
        try:
            res = requests.get(URL_BINANCE + sym, timeout=5)
            data = res.json()
            price = float(data["price"])
            msg += f"{name}: {price:,.2f} USDT\n"
        except Exception as e:
            logger.error(f"Lỗi coin {name}: {e}")
            msg += f"{name}: Lỗi\n"
    return msg

# ===============================================================
# LỆNH
# ===============================================================
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
    await update.message.reply_text(
        "Chào mừng đến với Gold & Coin Bot!\n\n"
        "/test - Kiểm tra bot\n"
        "/gia - Giá vàng BTMC\n"
        "/coin - Giá BTC, ETH\n\n"
        "Cập nhật tự động 8h sáng."
    )

async def gui_gia_vang_tu_dong():
    try:
        await _bot.send_message(chat_id=CHAT_ID, text=lay_gia_vang())
        logger.info("Gửi giá vàng tự động thành công!")
    except Exception as e:
        logger.error(f"Lỗi tự động: {e}")

# ===============================================================
# KHỞI TẠO BOT
# ===============================================================
async def setup_bot_async():
    global _main_loop, _bot, _is_ready
    from telegram.ext import ApplicationBuilder
    application = ApplicationBuilder().token(TOKEN).build()
    await application.initialize()
    await application.start()
    _bot = application.bot
    _main_loop = asyncio.get_event_loop()
    if not _main_loop.is_running():
        asyncio.set_event_loop(_main_loop)
    
    await application.bot.delete_webhook(drop_pending_updates=True)
    webhook_url = f"{DOMAIN}/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook: {webhook_url}")
    
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(gui_gia_vang_tu_dong(), _main_loop),
        "cron", hour=8, minute=0, timezone="Asia/Ho_Chi_Minh"
    )
    logger.info("Đã lên lịch gửi tự động 8h sáng")
    _is_ready = True

# ===============================================================
# WEBHOOK – TỰ GỌI HANDLER
# ===============================================================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    global _main_loop, _bot, _is_ready
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, _bot)
        if not update.message or not update.message.text:
            return "OK", 200
        
        text = update.message.text.strip().lower()
        logger.info(f"Nhận lệnh: {text}")
        
        start_time = time.time()
        while not _is_ready and time.time() - start_time < 10:
            time.sleep(0.1)
        
        if not _is_ready or not _main_loop or not _bot:
            logger.error("Bot chưa sẵn sàng")
            return "Error: Bot initializing", 503
        
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
    return "Bot đang chạy! Dùng /test để kiểm tra.", 200

# ===============================================================
# KHỞI ĐỘNG
# ===============================================================
threading.Thread(target=lambda: [time.sleep(2), asyncio.run(setup_bot_async())], daemon=True).start()