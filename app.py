import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import Flask, Response, request
import telebot

# ================== CONFIG ==================
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

API_WORLD = "https://giavanglive.com/api/get_gold_price_v2.php"
API_HAIHONG = "https://giavanglive.com/api/scrape_haihong.php"
API_MINHCHAU = "https://giavanglive.com/api/scrape_minhchau.php"
API_SILVER = "https://giavanglive.com/api/scrape_giabac.php"

# ================== HTTP SESSION & RETRY CONFIG ==================
session_http = requests.Session()
retries = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504]
)
session_http.mount("https://", HTTPAdapter(max_retries=retries))

# ================== REQUEST HELPER ==================
def fetch_api(url):
    try:
        full_url = f"{url}?t={int(time.time()*1000)}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://giavanglive.com/",
            "Accept": "application/json"
        }
        res = session_http.get(full_url, headers=headers, timeout=12)
        if res.status_code != 200:
            return None
        return res.json()
    except Exception as e:
        print("FETCH ERROR:", e)
        return None

# ================== DATA FUNCTIONS (GOLD & SILVER) ==================
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

# ================== STOCK FUNCTION (SSI IBOARD API) ==================
def get_stock_price(symbol: str):
    clean_symbol = symbol.strip()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://iboard.ssi.com.vn/",
        "Origin": "https://iboard.ssi.com.vn"
    }

    attempts = [clean_symbol.lower(), clean_symbol.upper()]
    json_data = None

    for i, sym in enumerate(attempts):
        url = f"https://iboard-query.ssi.com.vn/stock/{sym}?boardId=MAIN"
        try:
            # Thời gian timeout nâng lên 15s
            res = session_http.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                data_candidate = res.json()
                if data_candidate.get("code") == "SUCCESS" and data_candidate.get("data"):
                    json_data = data_candidate
                    break
        except requests.exceptions.Timeout:
            print(f"⏱️ Quá thời gian chờ khi kết nối đến {url}")
        except Exception as err:
            print(f"⚠️ Lỗi khi kết nối {url}: {err}")

        # Thêm thời gian chờ 0.4s giữa các lần thử
        if i < len(attempts) - 1:
            time.sleep(0.4)

    if not json_data:
        return f"❌ Server phản hồi chậm hoặc không tìm thấy dữ liệu cho mã `{clean_symbol.upper()}` trên SSI iBoard."

    data = json_data["data"]

    stock_symbol = data.get("stockSymbol", clean_symbol.upper())
    company_name = data.get("companyNameVi", stock_symbol)
    matched_price = data.get("matchedPrice", 0)
    change = data.get("priceChange", 0)
    percent = data.get("priceChangePercent", 0.0)
    volume = data.get("nmTotalTradedQty", 0)
    total_value = data.get("nmTotalTradedValue", 0)
    session_status = data.get("session", "N/A")

    ceil_price = data.get("ceiling", 0)
    floor_price = data.get("floor", 0)
    ref_price = data.get("refPrice", 0)
    high_price = data.get("highest", 0)
    low_price = data.get("lowest", 0)

    foreign_buy = data.get("buyForeignQtty", 0)
    foreign_sell = data.get("sellForeignQtty", 0)

    icon = "🟢" if change > 0 else ("🔴" if change < 0 else "🟡")
    sign = "+" if change > 0 else ""
    value_in_billion = total_value / 1_000_000_000

    return f"""📈 *{stock_symbol}* - {company_name}
💵 Giá khớp: *{matched_price:,.0f} VNĐ* ({icon} {sign}{change:,.0f} | {sign}{percent:.2f}%)
📊 Tổng KL: {volume:,.0f} CP (~{value_in_billion:,.2f} tỷ)
🏷 Trần/Sàn/TC: {ceil_price:,.0f} / {floor_price:,.0f} / {ref_price:,.0f}
↕️ Cao/Thấp: {high_price:,.0f} / {low_price:,.0f} (Phiên: {session_status})
🌐 Khối ngoại: Mua {foreign_buy:,.0f} | Bán {foreign_sell:,.0f} CP"""

# ================== TELEGRAM HANDLERS ==================
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "👋 Chào bạn!\n"
        "- Gõ /gold để xem giá vàng & bạc\n"
        "- Gõ /token <mã> hoặc /stock <mã> để tra bảng giá SSI (Ví dụ: `/token mbb`, `/token mbs`)"
    )

@bot.message_handler(commands=["gold"])
def gold(message):
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

@bot.message_handler(commands=["token", "stock"])
def stock(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(
            message,
            "⚠️ Vui lòng nhập kèm mã cổ phiếu.\nVí dụ: `/token mbb` hoặc `/stock mbs`",
            parse_mode="Markdown"
        )
        return

    symbol = parts[1]
    msg = bot.reply_to(
        message,
        f"⏳ Đang lấy dữ liệu `{symbol.upper()}` từ SSI iBoard...",
        parse_mode="Markdown"
    )

    result = get_stock_price(symbol)
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=msg.message_id,
        text=result,
        parse_mode="Markdown"
    )

# ================== FLASK ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def home():
    with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as f:
        html = f.read()

    html = html.replace("{{world}}", get_gold_world())
    html = html.replace("{{haihong}}", get_haihong())
    html = html.replace("{{minhchau}}", get_minhchau())
    html = html.replace("{{silver}}", get_silver())

    return Response(html, mimetype="text/html")

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
    bot.set_webhook(url="https://gold-coin-telebot.onrender.com/webhook")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
