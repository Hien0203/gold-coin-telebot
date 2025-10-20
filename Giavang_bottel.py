import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import datetime
import nest_asyncio

# --- THÔNG TIN CẤU HÌNH ---
BOT_TOKEN = "8454443915:AAHkjDGRj8Jqm_w4sEnhELVhxNODnAnPKA8"  # ← Token bot Telegram của bạn
CHAT_ID = 1624322977  # ← ID của bạn (lấy bằng @userinfobot)
URL_VANG = "https://btmc.vn/"
URL_BINANCE = "https://api.binance.com/api/v3/ticker/price?symbol="

# ===============================================================
# 🟡 HÀM LẤY GIÁ VÀNG BẢO TÍN MINH CHÂU
# ===============================================================
def lay_gia_vang():
    try:
        res = requests.get(URL_VANG, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        bang = soup.find("table", {"class": "bd_price_home"})
        if not bang:
            return "⚠️ Không tìm thấy dữ liệu giá vàng!"

        rows = bang.find_all("tr")[1:]  # bỏ hàng tiêu đề
        result = []

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                loai = cols[1].get_text(" ", strip=True)
                hamluong = cols[2].get_text(" ", strip=True)
                mua = cols[3].get_text(" ", strip=True)
                ban = cols[4].get_text(" ", strip=True)
                if mua or ban:
                    result.append(f"🏅 {loai}\nHàm lượng: {hamluong}\n💰 Mua: {mua or '–'} | 💵 Bán: {ban or '–'}")

        note = soup.find("p", class_="note")
        capnhat = note.get_text(strip=True).replace("Nguồn: www.btmc.vn", "").strip() if note else ""

        text = f"🌟 GIÁ VÀNG BẢO TÍN MINH CHÂU 🌟\n{capnhat}\n\n" + "\n\n".join(result)
        return text
    except Exception as e:
        return f"❌ Lỗi khi lấy dữ liệu giá vàng: {e}"


# ===============================================================
# 🪙 HÀM LẤY GIÁ COIN TỪ BINANCE
# ===============================================================
def lay_gia_coin():
    symbols = ["AVNTUSDT", "TREEUSDT", "ASTERUSDT","SOMIUSDT"]
    msg = "💹 GIÁ COIN (Binance) 💹\n\n"

    for sym in symbols:
        try:
            res = requests.get(URL_BINANCE + sym, timeout=5)
            data = res.json()
            if "price" in data:
                price = float(data["price"])
                msg += f"🪙 {sym.replace('USDT', '')}/USDT: {price:,.4f}\n"
            else:
                msg += f"⚠️ {sym.replace('USDT', '')}: Không có dữ liệu\n"
        except Exception as e:
            msg += f"⚠️ {sym.replace('USDT', '')}: Lỗi ({e})\n"

    return msg.strip()


# ===============================================================
# 🔘 LỆNH /gia — XEM GIÁ VÀNG
# ===============================================================
async def gia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = lay_gia_vang()
    await update.message.reply_text(msg)


# ===============================================================
# 🔘 LỆNH /coin — XEM GIÁ COIN
# ===============================================================
async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = lay_gia_coin()
    await update.message.reply_text(msg)


# ===============================================================
# 🔁 GỬI GIÁ VÀNG TỰ ĐỘNG HÀNG NGÀY
# ===============================================================
async def gui_tu_dong(app):
    msg = lay_gia_vang()
    today = datetime.date.today().strftime("%d/%m/%Y")
    text = f"⏰ Cập nhật giá vàng ngày {today}\n\n{msg}"
    await app.bot.send_message(chat_id=CHAT_ID, text=text)
    print("✅ Đã gửi giá vàng tự động thành công!")


# ===============================================================
# 🚀 HÀM MAIN — KHỞI CHẠY BOT
# ===============================================================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Lệnh thủ công
    app.add_handler(CommandHandler("gia", gia))
    app.add_handler(CommandHandler("coin", coin))

    # Scheduler: gửi tự động mỗi 08:00 sáng
    scheduler = BackgroundScheduler()

    def job():
        asyncio.create_task(gui_tu_dong(app))

    scheduler.add_job(job, "cron", hour=8, minute=0)
    scheduler.start()

    print("🤖 Bot đang chạy... Gõ /gia để xem giá vàng, /coin để xem giá coin (AVNT, TREE, ASTER, AA, AMPHA).")
    await app.run_polling()


# ===============================================================
# 🧩 CHẠY CHƯƠNG TRÌNH
# ===============================================================
if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
