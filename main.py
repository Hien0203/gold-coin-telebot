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

# Cache for CoinGecko coin list (symbol -> ID mapping)
COIN_LIST_CACHE = None

# Static mapping (backup nếu cache chưa load)
COINGECKO_COIN_IDS_STATIC = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "ADA": "cardano",
    "SOL": "solana",
    # SOMI, AVNT, ASTER, TREE cần tên đầy đủ để thêm
}

def load_coingecko_coin_list():
    """Load and cache CoinGecko coin list once."""
    global COIN_LIST_CACHE
    if COIN_LIST_CACHE is not None:
        return COIN_LIST_CACHE
    
    try:
        logger.info("Đang load danh sách coin từ CoinGecko...")
        res = requests.get("https://api.coingecko.com/api/v3/coins/list", timeout=10)
        if res.status_code == 200:
            coins = res.json()
            cache = {}
            for coin in coins:
                symbol_lower = coin["symbol"].lower() if coin["symbol"] else ""
                if symbol_lower:
                    if symbol_lower not in cache:
                        cache[symbol_lower] = coin["id"]
            COIN_LIST_CACHE = cache
            logger.info(f"Đã load {len(cache)} symbols từ CoinGecko.")
            return cache
        else:
            logger.error(f"Lỗi load coin list: {res.status_code}")
            return COINGECKO_COIN_IDS_STATIC
    except Exception as e:
        logger.error(f"Lỗi load coin list: {e}")
        return COINGECKO_COIN_IDS_STATIC

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

# Fetch coin prices from Binance
def lay_gia_binance(symbol):
    try:
        res = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT", timeout=5)
        data = res.json()
        if "code" not in data or data["code"] == 200:
            price = float(data["lastPrice"])
            price_change_percent = float(data["priceChangePercent"])
            percent_str = f"{'+' if price_change_percent >= 0 else ''}{price_change_percent:.2f}%"
            return f"📈 {symbol}: {price:,.5f} USDT ({percent_str})"
        return None
    except Exception as e:
        logger.error(f"Lỗi lấy giá {symbol} từ Binance: {e}")
        return None

# Fetch coin prices from CoinGecko
def lay_gia_coingecko(symbol):
    symbol_lower = symbol.lower()
    
    # Load cache nếu chưa có
    coin_list = load_coingecko_coin_list()
    
    # Tìm coin ID từ cache hoặc static
    coin_id = coin_list.get(symbol_lower)
    if not coin_id:
        coin_id = COINGECKO_COIN_IDS_STATIC.get(symbol)
    
    if not coin_id:
        return f"🚫 Không tìm thấy coin {symbol} trên CoinGecko. Vui lòng kiểm tra ký hiệu hoặc cung cấp tên đầy đủ (VD: 'Bitcoin' cho BTC)."
    
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
        return f"📈 {symbol}: {price:,.5f} USD ({percent_str}) [CoinGecko - Real-time]"
    except Exception as e:
        logger.error(f"Lỗi lấy giá {symbol} từ CoinGecko: {e}")
        return f"🚫 Lỗi mạng, không thể lấy giá {symbol} từ CoinGecko."

# Fetch coin prices with fallback (for /coin)
def lay_gia_coin(symbol):
    # Try Binance first
    result = lay_gia_binance(symbol)
    if result:
        return result
    logger.info(f"Binance không có {symbol}, thử CoinGecko.")
    return lay_gia_coingecko(symbol)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "👋 Chào mừng đến với Gold & Coin Bot! Dùng các lệnh sau để tra cứu:\n"
        "- /test ✅ Kiểm tra bot\n"
        "- /vang 🪙 Giá vàng BTMC\n"
        "- /coin 📈 Giá BTC, ETH, SOMI, AVNT, ASTER, TREE (Binance/CoinGecko)\n"
        "- /tuchon <ký hiệu> 🔍 Tra giá coin (ưu tiên Binance, nếu không có thì CoinGecko) (VD: /tuchon BTC)\n\n"
        "- /stock <mã> 📊 Tra giá chứng khoán VN (VD: /stock MBB)\n\n"
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
            # Thử Binance trước
            result = lay_gia_binance(symbol)
            if result:
                await update.message.reply_text(result)
                break
            logger.info(f"Binance không có {symbol}, thử CoinGecko.")
            # Fallback sang CoinGecko
            msg = lay_gia_coingecko(symbol)
            await update.message.reply_text(msg)
            break
        except NetworkError as e:
            logger.error(f"Lỗi mạng (lần {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                await update.message.reply_text("🚫 Lỗi mạng, không thể lấy giá coin.")

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
# Thêm hàm lấy giá cổ phiếu từ Simplize
def lay_gia_chungkhoan(symbol):
    try:
        url = f"https://simplize.vn/co-phieu/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return f"🚫 Lỗi kết nối đến Simplize.vn cho {symbol}."
        
        soup = BeautifulSoup(res.text, "html.parser")
        div = soup.find("div", class_="simplize-row simplize-row-middle")
        if not div:
            return f"🚫 Không tìm thấy dữ liệu giá cho {symbol}."
        
        price_elem = div.find("p", class_="css-19r22fg")
        change_elem = div.find("p", class_="css-1ei6h64")
        percent_elem = div.find("span", class_="css-fh5vtb")
        
        price = price_elem.get_text(strip=True) if price_elem else "N/A"
        change = change_elem.get_text(strip=True) if change_elem else "N/A"
        percent = percent_elem.get_text(strip=True) if percent_elem else "N/A"
        
        return f"📈 {symbol}: {price} ({change}) {percent}%"
    except Exception as e:
        logger.error(f"Lỗi lấy giá {symbol}: {e}")
        return f"🚫 Không thể lấy giá cho {symbol} do lỗi hệ thống."
# Thêm handler cho lệnh /stock
async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔍 Vui lòng nhập mã chứng khoán (VD: /stock MBB).")
        return
    symbol = context.args[0].upper()
    max_retries = 3
    for attempt in range(max_retries):
        try:
            msg = lay_gia_chungkhoan(symbol)
            await update.message.reply_text(msg)
            break
        except NetworkError as e:
            logger.error(f"Lỗi mạng (lần {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                await update.message.reply_text("🚫 Lỗi mạng, không thể lấy dữ liệu chứng khoán.")
def main():
    # Load CoinGecko cache on startup
    load_coingecko_coin_list()
    
    # Initialize application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test))
    application.add_handler(CommandHandler("vang", vang))
    application.add_handler(CommandHandler("coin", coin))
    application.add_handler(CommandHandler("tuchon", tuchon))
    application.add_handler(CommandHandler("stock", stock))

    # --- Lên lịch gửi tự động 3 lần/ngày ---
    application.job_queue.run_daily(
        send_auto_vang,
        time(hour=1, minute=0),    # 08:00 VN (UTC+7)
        days=(0, 1, 2, 3, 4, 5, 6),
    )

    application.job_queue.run_daily(
        send_auto_vang,
        time(hour=8, minute=0),    # 15:00 VN
        days=(0, 1, 2, 3, 4, 5, 6),
    )

    application.job_queue.run_daily(
        send_auto_vang,
        time(hour=13, minute=0),   # 20:00 VN
        days=(0, 1, 2, 3, 4, 5, 6),
    )
    # Start bot with polling in the main thread
    logger.info("Bot đang chạy...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()