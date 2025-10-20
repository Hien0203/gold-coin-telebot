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
# CẤU HÌNH
# ===============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN chưa được thiết lập!")
if not CHAT_ID:
    raise ValueError("CHAT_ID chưa được thiết lập!")

URL_VANG = "https://btmc.vn/trang-vang"
URL_BINANCE = "https://api.binance.com/api/v3/ticker/price?symbol="

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
                loai = cols[1].get_text(strip=True)
                hamluong = cols[2].get_text(strip=True)
                mua = cols[3].get_text(strip=True).replace(",", ".")
                ban = cols[4].get_text(strip=True).replace(",", ".")
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
# LẤY GIÁ COIN
# ===============================================================
def lay_gia_coin():
    symbols = ["AVNTUSDT", "TREEUSDT", "ASTERUSDT", "SOMIUSDT", "AAUSDT", "AMPHAUSDT"]
    msg = "GIÁ COIN (Binance)\n\n"
    for sym in symbols:
        try:
            res = requests.get(URL_BINANCE + sym, timeout=5)
            data = res.json()
            price = float(data["price"])
            coin = sym.replace("USDT", "")
            msg += f"{coin}/USDT: {price:,.4f}\n"
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
# GỬI TỰ ĐỘNG (chạy trong thread riêng)
# ===============================================================
def gui_gia_vang_tu_dong_sync():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        msg = lay_gia_vang()
        today = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        text = f"Cập nhật giá vàng {today}\n\n{msg}"
        # Gửi tin nhắn qua bot (cần truy cập app.bot)
        loop.run_until_complete(app.bot.send_message(chat_id=CHAT_ID, text=text))
        logger.info("Đã gửi giá vàng tự động!")
    except Exception as e:
        logger.error(f"Lỗi gửi tin tự động: {e}")
    finally:
        loop.close()

# ===============================================================
# MAIN
# ===============================================================
async def main():
    global app
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("gia", gia))
    app.add_handler(CommandHandler("coin", coin))

    # Dùng BackgroundScheduler (thread riêng)
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        gui_gia_vang_tu_dong_sync,
        "cron",
        hour=8,
        minute=0,
        timezone="Asia/Ho_Chi_Minh"
    )
    scheduler.start()

    logger.info("Bot đang chạy... /gia | /coin")
    await app.run_polling()

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