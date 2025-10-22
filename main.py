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

# Escape special characters for MarkdownV2
def escape_markdown_v2(text):
    """Escape special characters for Telegram's MarkdownV2."""
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

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
            # Escape special characters for MarkdownV2
            loai = escape_markdown_v2(loai)
            ham_luong = escape_markdown_v2(ham_luong)
            mua = escape_markdown_v2(mua)
            ban = escape_markdown_v2(ban)
            result.append(f"🪙 *{loai}* \\({ham_luong}\\)\n- Mua: {mua}\n- Bán: {ban}")
        return "*GIÁ VÀNG BTMC* 🪙\n\n" + "\n\n".join(result) if result else "🚫 Không có dữ liệu."
    except Exception as e:
        logger.error(f"Lỗi lấy vàng: {e}")
        return "🚫 Không thể lấy giá vàng do lỗi hệ thống."

# Fetch coin prices and 24-hour price change from Binance
def lay_gia_coin(symbol):
    try:
        res = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT", timeout=5)
        data = res.json()
        if "code" in data and data["code"] != 200:
            return f"🚫 Không tìm thấy cặp *{escape_markdown_v2(symbol)}/USDT* trên Binance."
        price = float(data["lastPrice"])
        price_change_percent = float(data["priceChangePercent"])
        # Format percentage with + or - and 2 decimal places
        percent_str = f"{'+' if price_change_percent >= 0 else ''}{price_change_percent:.2f}"
        percent_str = escape_markdown_v2(percent_str) + "\\%"
        return f"📈 *{escape_markdown_v2(symbol)}*: {price:,.2f} USDT \\({percent_str}\\)"
    except Exception as e:
        logger.error(f"Lỗi lấy giá {symbol}: {e}")
        return f"🚫 Không tìm thấy giá cho *{escape_markdown_v2(symbol)}* hoặc lỗi mạng."

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        f"{escape_markdown_v2('Chào mừng đến với Gold & Coin Bot! Dùng các lệnh sau để tra cứu:')}\n"
        f"\\- `/test` ✅ Kiểm tra bot\n"
        f"\\- `/vang` 🪙 Giá vàng BTMC\n"
        f"\\- `/coin` 📈 Giá BTC, ETH, SOMI, AVNT, ASTER, TREE\n"
        f"\\- `/tuchon <ký hiệu>` 🔍 Tra giá coin tùy chọn (VD: `/tuchon BTC`)\n\n"
        f"{escape_markdown_v2('Bot tự động gửi giá vàng lúc 8h sáng (VN time)!')}"
    )
    await update.message.reply_text(
        f"👋 *{message}*",
        parse_mode="MarkdownV2"
    )

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ *Bot hoạt động 100\\%!*", parse_mode="MarkdownV2")

async def vang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            msg = lay_gia_vang()
            await update.message.reply_text(msg, parse_mode="MarkdownV2")
            break
        except NetworkError as e:
            logger.error(f"Lỗi mạng (lần {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                await update.message.reply_text("🚫 *Lỗi mạng, không thể lấy dữ liệu vàng.*", parse_mode="MarkdownV2")

async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            msg = "*GIÁ COIN (Binance)* 📈\n\n" + "\n\n".join([lay_gia_coin(sym) for sym in ["BTC", "ETH", "SOMI", "AVNT", "ASTER", "TREE"]])
            await update.message.reply_text(msg, parse_mode="MarkdownV2")
            break
        except NetworkError as e:
            logger.error(f"Lỗi mạng (lần {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                await update.message.reply_text("🚫 *Lỗi mạng, không thể lấy dữ liệu coin.*", parse_mode="MarkdownV2")

async def tuchon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔍 *Vui lòng nhập ký hiệu coin* (VD: `/tuchon BTC`).", parse_mode="MarkdownV2")
        return
    symbol = context.args[0].upper()
    max_retries = 3
    for attempt in range(max_retries):
        try:
            msg = lay_gia_coin(symbol)
            await update.message.reply_text(msg, parse_mode="MarkdownV2")
            break
        except NetworkError as e:
            logger.error(f"Lỗi mạng (lần {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                await update.message.reply_text("🚫 *Lỗi mạng, không thể lấy dữ liệu coin.*", parse_mode="MarkdownV2")

# Scheduled task for sending gold prices
async def send_auto_vang(context: ContextTypes.DEFAULT_TYPE):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            msg = lay_gia_vang()
            await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="MarkdownV2")
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