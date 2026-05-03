import requests
from flask import Flask, request
import telebot
import os
import time

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# ================== API ==================
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

        if res.status_code != 200:
            print("HTTP ERROR:", res.status_code)
            return None

        return res.json()

    except Exception as e:
        print("FETCH ERROR:", e)
        return None

# ================== FUNCTIONS ==================
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
        return "❌ Không có dữ liệu"

    item = items[0]

    return f"""🏪 Hải Hồng:
{item.get('name')}
Mua: {item.get('buy_raw')}
Bán: {item.get('sell_raw')}"""

def get_minhchau():
    data = fetch_api(API_MINHCHAU)
    if not data or len(data) == 0:
        return "❌ Lỗi Minh Châu"

    item = data[0]

    return f"""💎 Minh Châu:
{item.get('name')}
Mua: {item.get('buy')}
Bán: {item.get('sell')}"""

def get_silver():
    data = fetch_api(API_SILVER)
    if not data or len(data) == 0:
        return "❌ Lỗi bạc"

    item = data[0]

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
    msg = "⏳ Đang lấy dữ liệu...\n\n"

    msg += get_gold_world() + "\n\n"
    msg += get_haihong() + "\n\n"
    msg += get_minhchau() + "\n\n"
    msg += get_silver()

    bot.reply_to(message, msg)

# ================== FLASK ==================
@app.route("/")
def home():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# ================== MAIN ==================
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(
        url="https://gold-coin-telebot.onrender.com/webhook"
    )

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
