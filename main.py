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

# Mapping of coin symbols to CoinGecko IDs
COINGECKO_COIN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOMI": None,  # Unknown; needs clarification
    "AVNT": None,  # Unknown; needs clarification
    "ASTER": None,  # Unknown; needs clarification
    "TREE": None,  # Unknown; needs clarification
}

# Fetch gold prices from BTMC
def lay_gia_vang():
    try:
        res = requests.get("https://btmc.vn", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if res.status_code != 200:
            return "🚫 Trang BTMC đang bảo trì."
        soup = BeautifulSoup(res.text, "html.parser")
        bang = soup.find("table", {"class": "bd_price_home"})
        if not bang:
            return "🚫 Không tìm thấy bảng giá vàng."
        rows = bang.find_all("tr")[1:]  # Skip header
        result = []
        for row in rows:
            cols = row.find_all("td")
            if not cols:
                continue
            # Handle rowspan
            if cols[0].has_attr("rowspan"):
                loai = cols[1].get_text(strip=True).split("\n")[0]
            else:
                loai = cols[0].get_text(strip=True).split("\n")[0]
            ham_luong = cols[2].find("b").get_text(strip=True) if cols[2].find("b") else "N/A"
            mua = cols[3].find("b").get_text(strip=True) if cols[3].find("b") else "N/A"
            ban = cols[4].find("b").get_text(strip=True) if cols[4].find("b") else cols[4].get_text(strip=True).replace("Liên hệ", "N/A")
            result.append(f"🪙 {loai} ({ham_luong})\n  Mua: {mua}\n  Bán: {ban}")
        return "GIÁ VÀNG BTMC 🪙\n\n" + "\n\n".join(result) if result else "🚫 Không có dữ liệu."
    except Exception as e:
        logger.error(f"Lỗi lấy vàng: {e}")
        return "🚫 Không thể lấy giá vàng do lỗi hệ thống."

# Fetch coin prices and 24-hour price change from Binance or CoinGecko
def lay_gia_coin(symbol):
    # Try Binance first
    try:
        res = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT", timeout=5)
        data = res.json()
        if "code" not in data or data["code"] == 200:
            price = float(data["lastPrice"])
            price_change_percent = float(data["priceChangePercent"])
            percent_str = f"{'+' if price_change_percent >= 0 else ''}{price_change_percent:.2f}%"
            return f"📈 {symbol}: {price:,.2f} USDT ({percent_str})"
        logger.info(f"Binance: Không tìm thấy cặp {symbol}/USDT, thử CoinGecko.")
    except Exception as e:
        logger.error(f"Lỗi lấy giá {symbol} từ Binance: {e}")

    # Fall back to CoinGecko
    coin_id = COINGECKO_COIN_IDS.get(symbol)
    if not coin_id:
        return f"🚫 Không tìm thấy cặp {symbol}/USDT trên Binance hoặc CoinGecko (coin ID không xác định)."
    try:
        res = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true",
            timeout=5
        )
        data = res.json()
        if coin_id not in data or not data[coin_id]:
            return f"🚫 Không tìm thấy giá cho {symbol} trên CoinGecko."
        price = float(data[coin_id]["usd"])
        price_change_percent = float(data[coin_id]["usd_24h_change"])
        percent_str = f"{'+' if price_change_percent >= 0 else ''}{price_change_percent:.2f}%"
        return f"📈 {symbol}: {price:,.2f} USD ({percent_str}) [CoinGecko]"
    except Exception as e:
        logger.error(f"Lỗi lấy giá {symbol} từ CoinGecko: {e}")
        return f"🚫 Không tìm thấy giá cho {symbol} trên Binance hoặc CoinGecko."

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "👋 Chào mừng đến với Gold & Coin Bot! Dùng các lệnh sau để tra cứu:\n"
        "- /test ✅ Kiểm tra bot\n"
        "- /vang 🪙 Giá vàng BTMC\n"
        "- /coin 📈 Giá BTC, ETH, SOMI, AVNT, ASTER, TREE\n"
        "- /tuchon <ký hiệu> 🔍 Tra giá coin tùy chọn (VD: /tuchon BTC)\n\n"
        "📅 Bot tự động gửi giá vàng lúc 8h sáng (VN time)!"
    )
    await update.message.reply_text(message)

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot hoạt động 100%!")

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
                await update.message.reply_text("🚫 Lỗi mạng, không thể lấy dữ liệu vàng.")

async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            msg = "GIÁ COIN (Binance/CoinGecko) 📈\n\n" + "\n\n".join([lay_gia_coin(sym) for sym in ["BTC", "ETH", "SOMI", "AVNT", "ASTER", "TREE"]])
            await update.message.reply_text(msg)
            break
        except NetworkError as e:
            logger.error(f"Lỗi mạng (lần {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                await update.message.reply_text("🚫 Lỗi mạng, không thể lấy dữ liệu coin.")

async def tuchon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔍 Vui lòng nhập ký hiệu coin (VD: /tuchon BTC).")
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
                await update.message.reply_text("🚫 Lỗi mạng, không thể lấy dữ liệu coin.")

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