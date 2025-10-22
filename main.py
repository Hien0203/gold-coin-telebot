import os
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import NetworkError
import asyncio
from datetime import time

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get token and CHAT_ID from environment variables
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Fetch gold prices from BTMC
def lay_gia_vang():
    try:
        res = requests.get("https://btmc.vn", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if res.status_code != 200:
            return "Trang BTMC đang bảo trì."
        soup = BeautifulSoup(res.text, "html.parser")
        bang = soup.find("table", {"class": "bd_price_home"})
        if not bang:
            return "Không tìm thấy bảng giá vàng."
        rows = bang.find_all("tr")[1:]  # Skip header
        result = []
        for row in rows:
            cols = row.find_all("td")
            if not cols:
                continue
            # Handle rowspan
            if cols[0].has_attr("rowspan"):
                loai = cols[1].get_text(strip=True).split("\n")[0]  # Get gold type
            else:
                loai = cols[0].get_text(strip=True).split("\n")[0]
            ham_luong = cols[2].find("b").get_text(strip=True) if cols[2].find("b") else "N/A"
            mua = cols[3].find("b").get_text(strip=True) if cols[3].find("b") else "N/A"
            ban = cols[4].find("b").get_text(strip=True) if cols[4].find("b") else cols[4].get_text(strip=True).replace("Liên hệ", "N/A")
            result.append(f"{loai} ({ham_luong})\nMua: {mua} | Bán: {ban}")
        return "GIÁ VÀNG BTMC\n" + "\n".join(result) if result else "Không có dữ liệu."
    except Exception as e:
        logger.error(f"Lỗi lấy vàng: {e}")
        return "Không thể lấy giá vàng."

# Fetch coin prices from Binance
def lay_gia_coin(symbol):
    try:
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT", timeout=5)
        data = res.json()
        price = float(data["price"])
        return f"Giá {symbol}: {price:,.2f} USDT"
    except Exception as e:
        logger.error(f"Lỗi lấy giá {symbol}: {e}")
        return f"Không tìm thấy giá cho {symbol} hoặc lỗi mạng."

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Chào mừng đến với Gold & Coin Bot!\n\n"
        "/test - Kiểm tra bot\n"
        "/vang - Giá vàng BTMC\n"
        "/coin - Giá Coin\n"
        "/tuchon <ký hiệu> - Kiểm tra giá coin tùy chọn (VD: /tuchon BTC)\n"
        "Tự động gửi giá vàng lúc 8h sáng!"
    )

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot hoạt động 100%!")

async def vang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            msg = lay_gia_vang()
            await update.message.reply_text(msg)
            break
        except NetworkError as e:
            logger.error(f"Lỗi mạng (lần {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                await update.message.reply_text("Lỗi mạng, không thể lấy dữ liệu vàng.")

async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            msg = "GIÁ COIN (Binance)\n\n" + "\n".join([lay_gia_coin(sym) for sym in ["BTC", "ETH","SOMI","AVNT","ASTER","TREE"]])
            await update.message.reply_text(msg)
            break
        except NetworkError as e:
            logger.error(f"Lỗi mạng (lần {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                await update.message.reply_text("Lỗi mạng, không thể lấy dữ liệu coin.")

async def tuchon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Vui lòng nhập ký hiệu coin (VD: /tuchon BTC).")
        return
    symbol = context.args[0].upper()
    max_retries = 3
    for attempt in range(max_retries):
        try:
            msg = lay_gia_coin(symbol)
            await update.message.reply_text(msg)
            break
        except NetworkError as e:
            logger.error(f"Lỗi mạng (lần {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                await update.message.reply_text("Lỗi mạng, không thể lấy dữ liệu coin.")

# Scheduled task for sending gold prices
async def send_auto_vang(context: ContextTypes.DEFAULT_TYPE):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            msg = lay_gia_vang()
            await context.bot.send_message(chat_id=CHAT_ID, text=msg)
            logger.info("Đã gửi giá vàng tự động!")
            break
        except NetworkError as e:
            logger.error(f"Lỗi mạng khi gửi tự động (lần {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                logger.error("Không thể gửi sau nhiều lần thử.")

def main():
    # Initialize application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test))
    application.add_handler(CommandHandler("vang", vang))
    application.add_handler(CommandHandler("coin", coin))
    application.add_handler(CommandHandler("tuchon", tuchon))

    # Schedule daily gold price message at 8:00 AM VN time (15:00 UTC)
    application.job_queue.run_daily(
        send_auto_vang,
        time(hour=15, minute=0),  # 15:00 UTC = 8:00 AM VN time
        days=(0, 1, 2, 3, 4, 5, 6),  # Every day
    )

    # Start bot with polling in the main thread
    logger.info("Bot đang chạy...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()