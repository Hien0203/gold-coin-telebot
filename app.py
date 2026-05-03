import requests
from bs4 import BeautifulSoup
from flask import Flask, request
import telebot
import os

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

URL = "https://giavanglive.com/"
# ================== API ==================
API_WORLD = "https://giavanglive.com/api/get_gold_price_v2.php"
API_HAIHONG = "https://giavanglive.com/api/scrape_haihong.php"
API_MINHCHAU = "https://giavanglive.com/api/scrape_minhchau.php"
API_SILVER = "https://giavanglive.com/api/scrape_giabac.php"
# ================== FUNCTIONS ==================
def get_gold_world():
    try:
        res = requests.get(API_WORLD, timeout=10)
        data = res.json()

        return f"""🌍 Giá vàng thế giới:
💰 {data.get("price", "N/A")} USD
📉 {data.get("change", "")} ({data.get("percent", "")})"""
    except:
        return "❌ Lỗi vàng thế giới"


def get_haihong():
    try:
        res = requests.get(API_HAIHONG, timeout=10)
        data = res.json()
        item = data[0]

        return f"""🏪 Hải Hồng:
{item['name']}
Mua: {item['buy']}
Bán: {item['sell']}"""
    except:
        return "❌ Lỗi Hải Hồng"


def get_minhchau():
    try:
        res = requests.get(API_MINHCHAU, timeout=10)
        data = res.json()
        item = data[0]

        return f"""💎 Minh Châu:
{item['name']}
Mua: {item['buy']}
Bán: {item['sell']}"""
    except:
        return "❌ Lỗi Minh Châu"


def get_silver():
    try:
        res = requests.get(API_SILVER, timeout=10)
        data = res.json()
        item = data[0]

        return f"""🥈 Bạc:
{item['name']}
Mua: {item['buy']}
Bán: {item['sell']}"""
    except:
        return "❌ Lỗi bạc"


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


@app.route("/")
def home():
    return "Bot is running!"

# ✅ webhook đúng
@app.route("/webhook", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url="https://gold-coin-telebot.onrender.com/webhook")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
