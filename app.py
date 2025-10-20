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

# Áp dụng nest_asyncio để tránh lỗi event loop
nest_asyncio.apply()

# ===============================================================
# CẤU HÌNH
# ===============================================================
TOKEN = os.getenv("BOT_TOKEN", "8454443915:AAHkjDGRj8Jqm_w4sEnhELVhxNODnAnPKA8")
CHAT_ID = int(os.getenv("CHAT_ID", "1624322977"))
DOMAIN = os.getenv("RENDER_EXTERNAL_URL", "https://gold-coin-telebot.onrender.com")

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tạo ứng dụng Telegram
telegram_app = ApplicationBuilder().token(TOKEN).build()

# URL
URL_VANG = "https://btmc.vn/trang-vang"
URL_BINANCE = "https://api.binance.com/api/v3/ticker/price?symbol="

# Scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# ===============================================================
# LẤY GIÁ VÀNG
# ===============================================================
def lay_gia_vang():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(URL_VANG, headers=headers, timeout=15)
        res.raise_for_status()
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        bang = soup.find("table", {"class": "bd_price_home"})
        if not bang:
            return "Không tìm thấy bảng giá vàng."

        rows = bang.find_all("tr")[1:]
        result = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                loai = cols[1].get_text(" ", strip=True)
                mua = cols[3].get_text(" ", strip=True).replace(",", ".")
                ban = cols[4].get_text(" ", strip=True).replace(",", ".")
                mua = mua if mua not in ["-", ""] else "–"
                ban = ban if ban not in ["-", ""] else "–"
                result.append(f"{loai}\nMua: {mua} | Bán: {ban}")

        note = soup.find("p", class_="note")
        capnhat = note.get_text(strip=True).replace("Nguồn: www.btmc.vn", "").strip() if note else "Cập nhật mới nhất"

        return f"GIÁ VÀNG BẢO TÍN MINH CHÂU\n{capnhat}\n\n" + "\n\n".join(result)
    except Exception as e:
        logger.error(f"Lỗi lấy giá vàng: {e}")
        return f"Lỗi: {e}"


# ===============================================================
# LẤY GIÁ COIN
# ===============================================================
def lay_gia_coin():
    symbols = {
        "AVNT": "AVNTUSDT",
        "TREE": "TREEUSDT",
        "ASTER": "ASTERUSDT",
        "SOMI": "SOMIUSDT"
    }
    msg = "GIÁ COIN (Binance)\n\n"
    for name, symbol in symbols.items():
        try:
            res = requests.get(URL_BINANCE + symbol, timeout=5)
            data = res.json()
            if "price" in data:
                price = float(data["price"])
                msg += f"{name}: {price:,.4f} USDT\n"
            else:
                msg += f"{name}: Không có dữ liệu\n"
        except Exception:
            msg += f"{name}: Lỗi\n"
    return msg.strip()


# ===============================================================
# LỆNH /gia
# ===============================================================
async def gia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = lay_gia_vang()
    await update.message.reply_text(msg)


# ===============================================================
# LỆNH /coin
# ===============================================================
async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = lay_gia_coin()
    await update.message.reply_text(msg)


# ===============================================================
# GỬI TỰ ĐỘNG 8H SÁNG
# ===============================================================
async def gui_gia_vang_tu_dong():
    try:
        msg = lay_gia_vang()
        today = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        text = f"Cập nhật giá vàng {today}\n\n{msg}"
        await telegram_app.bot.send_message(chat_id=CHAT_ID, text=text)
        logger.info("Đã gửi giá vàng tự động!")
    except Exception as e:
        logger.error(f"Lỗi gửi tự động: {e}")


# ===============================================================
# WEBHOOK ROUTE (ĐỒNG BỘ - DÙNG THREAD)
# ===============================================================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """Nhận update từ Telegram (đồng bộ, dùng thread để chạy async)"""
    try:
        data = request.get_json(force=True)
        text = data.get("message", {}).get("text", "unknown")
        logger.info(f"Webhook nhận lệnh: {text}")

        # Chạy async trong thread riêng
        def run_async_update():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                update = Update.de_json(data, telegram_app.bot)
                loop.run_until_complete(telegram_app.process_update(update))
            except Exception as e:
                logger.error(f"Lỗi xử lý update: {e}")
            finally:
                loop.close()

        thread = threading.Thread(target=run_async_update)
        thread.start()

        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook lỗi: {e}")
        return "Error", 500


@app.route("/", methods=["GET"])
def index():
    return "Bot đang chạy! Dùng /gia hoặc /coin", 200


# ===============================================================
# KHỞI TẠO WEBHOOK VÀ SCHEDULER
# ===============================================================
def setup_bot():
    logger.info("Đang thiết lập webhook...")
    try:
        # Xóa webhook cũ
        loop = asyncio.get_event_loop()
        loop.run_until_complete(telegram_app.bot.delete_webhook(drop_pending_updates=True))
        logger.info("Đã xóa webhook cũ.")

        # Thiết lập webhook mới
        webhook_url = f"{DOMAIN}/{TOKEN}"
        loop.run_until_complete(telegram_app.bot.set_webhook(url=webhook_url))
        logger.info(f"Webhook đã được thiết lập: {webhook_url}")

        # Lên lịch gửi tin 8h sáng
        scheduler.add_job(
            lambda: asyncio.run(gui_gia_vang_tu_dong()),
            "cron",
            hour=8,
            minute=0,
            timezone="Asia/Ho_Chi_Minh"
        )
        logger.info("Đã lên lịch gửi tin tự động 8:00 sáng (GMT+7)")
    except Exception as e:
        logger.error(f"Lỗi thiết lập bot: {e}")


# ===============================================================
# CHẠY ỨNG DỤNG
# ===============================================================
if __name__ == "__main__":
    # Thêm lệnh
    telegram_app.add_handler(CommandHandler("gia", gia))
    telegram_app.add_handler(CommandHandler("coin", coin))

    # Thiết lập webhook và scheduler
    setup_bot()

    # Chạy Flask
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Bot đang chạy trên port {port}...")
    app.run(host="0.0.0.0", port=port)