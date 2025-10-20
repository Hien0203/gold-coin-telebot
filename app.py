# app.py
import os
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import datetime
import logging
import nest_asyncio

# Áp dụng nest_asyncio để tránh lỗi event loop
nest_asyncio.apply()

# ===============================================================
# CẤU HÌNH (DÙNG BIẾN MÔI TRƯỜNG TRÊN RENDER)
# ===============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8454443915:AAHkjDGRj8Jqm_w4sEnhELVhxNODnAnPKA8")  # Dùng env nếu có
CHAT_ID = os.getenv("CHAT_ID", "1624322977")  # Dùng env nếu có
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "supersecret123")  # Tùy chọn
DOMAIN = os.getenv("RENDER_EXTERNAL_URL")  # Render tự động set

# Nếu không có domain → dùng localhost (chỉ test)
if not DOMAIN:
    DOMAIN = "https://your-bot.onrender.com"  # Thay bằng tên bot của bạn

URL_VANG = "https://btmc.vn/trang-vang"
URL_BINANCE = "https://api.binance.com/api/v3/ticker/price?symbol="

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================================================
# LẤY GIÁ VÀNG BẢO TÍN MINH CHÂU
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
                hamluong = cols[2].get_text(" ", strip=True)
                mua = cols[3].get_text(" ", strip=True).replace(",", ".")
                ban = cols[4].get_text(" ", strip=True).replace(",", ".")
                mua = mua if mua not in ["-", ""] else "–"
                ban = ban if ban not in ["-", ""] else "–"
                result.append(f"{loai}\nHàm lượng: {hamluong}\nMua: {mua} | Bán: {ban}")

        note = soup.find("p", class_="note")
        capnhat = note.get_text(strip=True).replace("Nguồn: www.btmc.vn", "").strip() if note else "Cập nhật mới nhất"

        return f"GIÁ VÀNG BẢO TÍN MINH CHÂU\n{capnhat}\n\n" + "\n\n".join(result)
    except Exception as e:
        logger.error(f"Lỗi lấy giá vàng: {e}")
        return f"Lỗi: {e}"


# ===============================================================
# LẤY GIÁ COIN TỪ BINANCE
# ===============================================================
def lay_gia_coin():
    symbols = ["AVNTUSDT", "TREEUSDT", "ASTERUSDT", "SOMIUSDT"]
    msg = "GIÁ COIN (Binance)\n\n"
    for sym in symbols:
        try:
            res = requests.get(URL_BINANCE + sym, timeout=5)
            data = res.json()
            if "price" in data:
                price = float(data["price"])
                coin = sym.replace("USDT", "")
                msg += f"{coin}/USDT: {price:,.4f}\n"
            else:
                msg += f"{sym.replace('USDT', '')}: Không có dữ liệu\n"
        except Exception as e:
            msg += f"{sym.replace('USDT', '')}: Lỗi\n"
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
async def gui_gia_vang_tu_dong(app):
    try:
        msg = lay_gia_vang()
        today = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        text = f"Cập nhật giá vàng {today}\n\n{msg}"
        await app.bot.send_message(chat_id=CHAT_ID, text=text)
        logger.info("Đã gửi giá vàng tự động!")
    except Exception as e:
        logger.error(f"Lỗi gửi tự động: {e}")


# ===============================================================
# MAIN – DÙNG WEBHOOK
# ===============================================================
async def main():
    global app
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Thêm lệnh
    app.add_handler(CommandHandler("gia", gia))
    app.add_handler(CommandHandler("coin", coin))

    # Scheduler: gửi 8h sáng
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: asyncio.create_task(gui_gia_vang_tu_dong(app)),
        "cron",
        hour=8,
        minute=0,
        timezone="Asia/Ho_Chi_Minh"
    )
    scheduler.start()

    # Webhook URL
    webhook_url = f"{DOMAIN}/{BOT_TOKEN}"

    # Xóa webhook cũ (nếu có)
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info(f"Đã xóa webhook cũ.")

    # Thiết lập webhook mới
    await app.bot.set_webhook(
        url=webhook_url,
        secret_token=WEBHOOK_SECRET
    )
    logger.info(f"Webhook đã được thiết lập: {webhook_url}")

    # Chạy webhook
    logger.info("Bot đang chạy với Webhook... /gia | /coin")
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=webhook_url,
        secret_token=WEBHOOK_SECRET
    )


# ===============================================================
# CHẠY CHƯƠNG TRÌNH
# ===============================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot đã dừng.")
    except Exception as e:
        logger.critical(f"Bot crash: {e}")