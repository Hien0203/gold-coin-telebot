import requests
from bs4 import BeautifulSoup
from flask import Flask, request
import telebot
import os

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

URL = "https://giavanglive.com/"

def get_gold_price():
    try:
        res = requests.get(URL, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        price = soup.select_one(".current-price").text.strip()
        change = soup.select_one(".price-badge").text.strip()

        return f"💰 Giá vàng thế giới:\n{price} USD\n{change}"
    except:
        return "❌ Lỗi lấy dữ liệu!"

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "👋 Gõ /gold để xem giá vàng")

@bot.message_handler(commands=["gold"])
def gold(message):
    bot.reply_to(message, get_gold_price())

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
