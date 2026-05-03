import requests
from flask import Flask, request, send_file
import telebot
import os
import time
from flask import render_template
# ================== CONFIG ==================
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

API_WORLD = "https://giavanglive.com/api/get_gold_price_v2.php"
API_HAIHONG = "https://giavanglive.com/api/scrape_haihong.php"
API_MINHCHAU = "https://giavanglive.com/api/scrape_minhchau.php"
API_SILVER = "https://giavanglive.com/api/scrape_giabac.php"

# ================== REQUEST HELPER ==================
def fetch_api(url):
    try:
        full_url = f"{url}?t={int(time.time()*1000)}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://giavanglive.com/",
            "Accept": "application/json"
        }

        res = requests.get(full_url, headers=headers, timeout=10)

        print("CALL:", full_url)
        print("STATUS:", res.status_code)

        if res.status_code != 200:
            return None

        return res.json()

    except Exception as e:
        print("FETCH ERROR:", e)
        return None

# ================== DATA FUNCTIONS ==================
def get_gold_world():
    data = fetch_api(API_WORLD)
    if not data:
        return "❌ Lỗi vàng thế giới"

    d = data.get("data", {})

    return f"""🌍 Giá vàng thế giới:
💰 {d.get("price", "N/A")} USD
📉 {d.get("change", "")} ({d.get("percent", "")}%)"""

def get_haihong():
    data = fetch_api(API_HAIHONG)
    if not data:
        return "❌ Lỗi Hải Hồng"

    items = data.get("data", [])
    if not items:
        return "❌ Không có dữ liệu Hải Hồng"

    item = items[0]

    return f"""🏪 Hải Hồng:
{item.get('name')}
Mua: {item.get('buy_raw')}
Bán: {item.get('sell_raw')}"""

def get_minhchau():
    data = fetch_api(API_MINHCHAU)
    if not data:
        return "❌ Lỗi Minh Châu"

    items = data.get("data", [])
    if not items:
        return "❌ Không có dữ liệu Minh Châu"

    item = items[0]

    return f"""💎 Minh Châu:
{item.get('name')}
Mua: {item.get('buy')}
Bán: {item.get('sell')}"""

def get_silver():
    data = fetch_api(API_SILVER)
    if not data:
        return "❌ Lỗi bạc"

    items = data.get("data", [])
    if not items:
        return "❌ Không có dữ liệu bạc"

    item = items[0]

    return f"""🥈 Bạc:
{item.get('name')}
Mua: {item.get('buy')}
Bán: {item.get('sell')}"""

# ================== TELEGRAM ==================
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "👋 Gõ /gold để xem giá vàng")

@bot.message_handler(commands=["gold"])
def gold(message):
    # trả lời ngay tránh timeout
    msg = bot.reply_to(message, "⏳ Đang lấy dữ liệu...")

    try:
        text = ""
        text += get_gold_world() + "\n\n"
        text += get_haihong() + "\n\n"
        text += get_minhchau() + "\n\n"
        text += get_silver()

        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg.message_id,
            text=text
        )
    except Exception as e:
        print("BOT ERROR:", e)
        bot.reply_to(message, "❌ Lỗi xử lý dữ liệu")

# ================== FLASK ==================
@app.route("/")
def home():
    return send_file(
        "index.html",
        world=get_gold_world(),
        haihong=get_haihong(),
        minhchau=get_minhchau(),
        silver=get_silver()
    )

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        print("WEBHOOK ERROR:", e)
        return "ERROR", 500

# ================== MAIN ==================
if __name__ == "__main__":
    print("🚀 Bot starting...")

    bot.remove_webhook()
    bot.set_webhook(
        url="https://gold-coin-telebot.onrender.com/webhook"
    )

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
