import os
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import schedule
import time

# Cấu hình logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Lấy token và CHAT_ID từ biến môi trường
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")  # Thay YOUR_BOT_TOKEN_HERE bằng token thật
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID_HERE")    # Thay YOUR_CHAT_ID_HERE bằng ID thật

# Lấy dữ liệu
def lay_gia_vang():
    try:
        res = requests.get("https://btmc.vn", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
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
            res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}", timeout=5)
            data = res.json()
            price = float(data["price"])
            msg += f"{name}: {price:,.2f} USDT\n"
        except Exception as e:
            logger.error(f"Lỗi coin {name}: {e}")
            msg += f"{name}: Lỗi\n"
    return msg

# Handler cho các lệnh
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Chào mừng đến với Gold & Coin Bot!\n\n"
        "/test - Kiểm tra bot\n"
        "/gia - Giá vàng BTMC\n"
        "/coin - Giá BTC, ETH\n"
        "Tự động gửi giá vàng lúc 8h sáng!"
    )

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot hoạt động 100%!")

async def gia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = lay_gia_vang()
    await update.message.reply_text(msg)

async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = lay_gia_coin()
    await update.message.reply_text(msg)

# Hàm gửi tự động
async def send_auto_vang(context: ContextTypes.DEFAULT_TYPE):
    msg = lay_gia_vang()
    await context.bot.send_message(chat_id=CHAT_ID, text=msg)
    logger.info("Đã gửi giá vàng tự động!")

def run_scheduled_tasks(application):
    # Lên lịch gửi giá vàng lúc 8h sáng (giờ địa phương)
    schedule.every().day.at("08:00").do(
        lambda: application.job_queue.run_once(send_auto_vang, when=0)
    )
    logger.info("Đã lên lịch gửi tự động lúc 8h sáng")

    # Vòng lặp chạy schedule
    while True:
        schedule.run_pending()
        time.sleep(60)  # Kiểm tra mỗi phút

def main():
    # Khởi tạo application với polling
    application = Application.builder().token(TOKEN).build()

    # Thêm handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test))
    application.add_handler(CommandHandler("gia", gia))
    application.add_handler(CommandHandler("coin", coin))

    # Bắt đầu bot
    logger.info("Bot đang chạy...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

    # Chạy các tác vụ tự động trong thread riêng
    import threading
    threading.Thread(target=lambda: run_scheduled_tasks(application), daemon=True).start()

if __name__ == '__main__':
    main()