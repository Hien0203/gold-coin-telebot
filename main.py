import asyncio
import logging
import os
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import NetworkError
from datetime import time
from dotenv import load_dotenv
import pytz  # THÊM DÒNG NÀY

# === LOAD ENV ===
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("Thiếu BOT_TOKEN hoặc CHAT_ID trong .env")

try:
    CHAT_ID = int(CHAT_ID)
except:
    raise ValueError("CHAT_ID phải là số!")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === CACHE & STATIC ===
COIN_LIST_CACHE = None
COINGECKO_COIN_IDS_STATIC = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOMI": "somi", "AVNT": "avant",
    "ASTER": "aster", "TREE": "tree"
}

def load_coingecko_coin_list():
    global COIN_LIST_CACHE
    if COIN_LIST_CACHE: return COIN_LIST_CACHE
    try:
        res = requests.get("https://api.coingecko.com/api/v3/coins/list", timeout=10)
        if res.status_code == 200:
            coins = res.json()
            COIN_LIST_CACHE = {c["symbol"].lower(): c["id"] for c in coins if c["symbol"]}
            logger.info(f"Load {len(COIN_LIST_CACHE)} coins.")
            return COIN_LIST_CACHE
    except Exception as e:
        logger.error(f"Lỗi load coin list: {e}")
    return COINGECKO_COIN_IDS_STATIC

# === LẤY DỮ LIỆU ===
def lay_gia_vang():
    try:
        res = requests.get("https://btmc.vn", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        bang = soup.find("table", {"class": "bd_price_home"})
        if not bang: return "Không tìm thấy bảng giá vàng."
        rows = bang.find_all("tr")[1:]
        result = []
        for row in rows:
            cols = row.find_all("td")
            if not cols: continue
            loai = cols[1].get_text(strip=True).split("\n")[0] if cols[0].has_attr("rowspan") else cols[0].get_text(strip=True).split("\n")[0]
            mua = cols[3].find("b").get_text(strip=True) if cols[3].find("b") else "N/A"
            ban = cols[4].find("b").get_text(strip=True) if cols[4].find("b") else "N/A"
            result.append(f"{loai}\n  Mua: {mua}\n  Bán: {ban}")
        return "GIÁ VÀNG BTMC\n\n" + "\n\n".join(result)
    except: return "Lỗi lấy giá vàng."

def lay_gia_coin(symbol):
    # Binance
    try:
        res = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT", timeout=5)
        data = res.json()
        if "code" not in data:
            p = float(data["lastPrice"])
            c = float(data["priceChangePercent"])
            return f"{symbol}: {p:,.5f} USDT ({'+' if c >= 0 else ''}{c:.2f}%)"
    except: pass

    # CoinGecko
    coin_list = load_coingecko_coin_list()
    coin_id = coin_list.get(symbol.lower()) or COINGECKO_COIN_IDS_STATIC.get(symbol)
    if not coin_id: return f"Không tìm thấy {symbol}"
    try:
        res = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true", timeout=5)
        data = res.json()
        if coin_id in data:
            p = data[coin_id]["usd"]
            c = data[coin_id]["usd_24h_change"]
            asyncio.run(asyncio.sleep(1.2))
            return f"{symbol}: {p:,.5f} USD ({'+' if c >= 0 else ''}{c:.2f}%) [CG]"
    except: pass
    return f"Lỗi giá {symbol}"

def lay_gia_chungkhoan(symbol):
    try:
        res = requests.get(f"https://simplize.vn/co-phieu/{symbol}", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        div = soup.find("div", class_="simplize-row simplize-row-middle")
        if not div: return f"Không tìm thấy {symbol}"
        price = div.find("p", class_="css-19r22fg")
        change = div.find("p", class_="css-1ei6h64")
        return f"{symbol}: {price.get_text(strip=True) if price else 'N/A'} ({change.get_text(strip=True) if change else 'N/A'})"
    except: return f"Lỗi giá {symbol}"

# === HANDLERS ===
async def start(update: Update, context):
    await update.message.reply_text("Dùng: /test /vang /coin /tuchon BTC /stock MBB")

async def test(update: Update, context):
    await update.message.reply_text("Bot OK!")

async def vang(update: Update, context):
    for _ in range(3):
        try:
            await update.message.reply_text(lay_gia_vang())
            return
        except NetworkError:
            await asyncio.sleep(2)
    await update.message.reply_text("Lỗi mạng.")

async def coin(update: Update, context):
    coins = ["BTC", "ETH", "SOMI", "AVNT", "ASTER", "TREE"]
    results = [lay_gia_coin(c) for c in coins]
    await update.message.reply_text("GIÁ COIN\n\n" + "\n\n".join(results))

async def tuchon(update: Update, context):
    if not context.args:
        await update.message.reply_text("Dùng: /tuchon BTC")
        return
    sym = context.args[0].upper()
    for _ in range(3):
        try:
            await update.message.reply_text(lay_gia_coin(sym))
            return
        except NetworkError:
            await asyncio.sleep(2)

async def stock(update: Update, context):
    if not context.args:
        await update.message.reply_text("Dùng: /stock MBB")
        return
    sym = context.args[0].upper()
    for _ in range(3):
        try:
            await update.message.reply_text(lay_gia_chungkhoan(sym))
            return
        except NetworkError:
            await asyncio.sleep(2)

async def send_auto_vang(context):
    for _ in range(3):
        try:
            await context.bot.send_message(chat_id=CHAT_ID, text=lay_gia_vang())
            logger.info("Gửi vàng tự động thành công.")
            return
        except NetworkError:
            await asyncio.sleep(2)

# === ASYNC MAIN ===
async def main():
    load_coingecko_coin_list()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("vang", vang))
    app.add_handler(CommandHandler("coin", coin))
    app.add_handler(CommandHandler("tuchon", tuchon))
    app.add_handler(CommandHandler("stock", stock))

    # ĐẶT TIMEZONE CHO SCHEDULER
    app.job_queue.scheduler.configure(timezone=pytz.timezone("Asia/Ho_Chi_Minh"))

    # LÊN LỊCH
    app.job_queue.run_repeating(
        send_auto_vang,
        interval=5*3600,
        first=time(hour=1, minute=0)  # 8h sáng VN
    )

    logger.info("Bot khởi động...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

# === CHẠY ===
if __name__ == '__main__':
    asyncio.run(main())