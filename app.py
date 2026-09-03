# import requests
# from flask import Flask, request, send_file
# import telebot
# import os
# import time
# from flask import render_template
# # ================== CONFIG ==================
# TOKEN = os.getenv("BOT_TOKEN")
# bot = telebot.TeleBot(TOKEN)

# app = Flask(__name__)

# API_WORLD = "https://giavanglive.com/api/get_gold_price_v2.php"
# API_HAIHONG = "https://giavanglive.com/api/scrape_haihong.php"
# API_MINHCHAU = "https://giavanglive.com/api/scrape_minhchau.php"
# API_SILVER = "https://giavanglive.com/api/scrape_giabac.php"

# # ================== REQUEST HELPER ==================
# def fetch_api(url):
#     try:
#         full_url = f"{url}?t={int(time.time()*1000)}"
#         headers = {
#             "User-Agent": "Mozilla/5.0",
#             "Referer": "https://giavanglive.com/",
#             "Accept": "application/json"
#         }

#         res = requests.get(full_url, headers=headers, timeout=10)

#         print("CALL:", full_url)
#         print("STATUS:", res.status_code)

#         if res.status_code != 200:
#             return None

#         return res.json()

#     except Exception as e:
#         print("FETCH ERROR:", e)
#         return None

# # ================== DATA FUNCTIONS ==================
# def get_gold_world():
#     data = fetch_api(API_WORLD)
#     if not data:
#         return "❌ Lỗi vàng thế giới"

#     d = data.get("data", {})

#     return f"""🌍 Giá vàng thế giới:
# 💰 {d.get("price", "N/A")} USD
# 📉 {d.get("change", "")} ({d.get("percent", "")}%)"""

# def get_haihong():
#     data = fetch_api(API_HAIHONG)
#     if not data:
#         return "❌ Lỗi Hải Hồng"

#     items = data.get("data", [])
#     if not items:
#         return "❌ Không có dữ liệu Hải Hồng"

#     item = items[0]

#     return f"""🏪 Hải Hồng:
# {item.get('name')}
# Mua: {item.get('buy_raw')}
# Bán: {item.get('sell_raw')}"""

# def get_minhchau():
#     data = fetch_api(API_MINHCHAU)
#     if not data:
#         return "❌ Lỗi Minh Châu"

#     items = data.get("data", [])
#     if not items:
#         return "❌ Không có dữ liệu Minh Châu"

#     item = items[0]

#     return f"""💎 Minh Châu:
# {item.get('name')}
# Mua: {item.get('buy')}
# Bán: {item.get('sell')}"""

# def get_silver():
#     data = fetch_api(API_SILVER)
#     if not data:
#         return "❌ Lỗi bạc"

#     items = data.get("data", [])
#     if not items:
#         return "❌ Không có dữ liệu bạc"

#     item = items[0]

#     return f"""🥈 Bạc:
# {item.get('name')}
# Mua: {item.get('buy')}
# Bán: {item.get('sell')}"""

# # ================== TELEGRAM ==================
# @bot.message_handler(commands=["start"])
# def start(message):
#     bot.reply_to(message, "👋 Gõ /gold để xem giá vàng")

# @bot.message_handler(commands=["gold"])
# def gold(message):
#     # trả lời ngay tránh timeout
#     msg = bot.reply_to(message, "⏳ Đang lấy dữ liệu...")

#     try:
#         text = ""
#         text += get_gold_world() + "\n\n"
#         text += get_haihong() + "\n\n"
#         text += get_minhchau() + "\n\n"
#         text += get_silver()

#         bot.edit_message_text(
#             chat_id=message.chat.id,
#             message_id=msg.message_id,
#             text=text
#         )
#     except Exception as e:
#         print("BOT ERROR:", e)
#         bot.reply_to(message, "❌ Lỗi xử lý dữ liệu")

# # ================== FLASK ==================
# # @app.route("/")
# # def home():
# #     return send_file(
# #         "index.html",
# #         world=get_gold_world(),
# #         haihong=get_haihong(),
# #         minhchau=get_minhchau(),
# #         silver=get_silver()
# #     )
# from flask import Response
# import os

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# @app.route("/")
# def home():
#     with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as f:
#         html = f.read()

#     # replace dữ liệu vào HTML
#     html = html.replace("{{world}}", get_gold_world())
#     html = html.replace("{{haihong}}", get_haihong())
#     html = html.replace("{{minhchau}}", get_minhchau())
#     html = html.replace("{{silver}}", get_silver())

#     return Response(html, mimetype="text/html")
# @app.route("/webhook", methods=["POST"])
# def webhook():
#     try:
#         json_str = request.get_data().decode("utf-8")
#         update = telebot.types.Update.de_json(json_str)
#         bot.process_new_updates([update])
#         return "OK", 200
#     except Exception as e:
#         print("WEBHOOK ERROR:", e)
#         return "ERROR", 500

# # ================== MAIN ==================
# if __name__ == "__main__":
#     print("🚀 Bot starting...")

#     bot.remove_webhook()
#     bot.set_webhook(
#         url="https://gold-coin-telebot.onrender.com/webhook"
#     )

#     app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

import os
import time
import requests
from bs4 import BeautifulSoup
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

# ================== PARSER HTML BẢNG GIÁ SSI IBOARD ==================
def parse_html_ssi_table(html_source: str, target_symbol: str):
    """
    Bóc tách dữ liệu cổ phiếu trực tiếp từ các thẻ HTML của AG-Grid trên SSI iBoard:
    - Tìm thẻ hàng: div[role='row'][row-id='MÃ']
    - Tìm thẻ cột theo col-id: matchedPrice, priceChange, priceChangePercent, nmTotalTradedQty, ceiling, floor, refPrice
    """
    try:
        soup = BeautifulSoup(html_source, "html.parser")
        symbol_upper = target_symbol.strip().upper()

        # Tìm dòng cổ phiếu qua thuộc tính row-id
        row = soup.find("div", attrs={"row-id": symbol_upper})
        if not row:
            return None

        def get_col_val(col_id):
            cell = row.find("div", attrs={"col-id": col_id})
            return cell.get_text(strip=True) if cell else "N/A"

        matched_price = get_col_val("matchedPrice")
        change = get_col_val("priceChange")
        percent = get_col_val("priceChangePercent")
        volume = get_col_val("nmTotalTradedQty")
        ceiling = get_col_val("ceiling")
        floor = get_col_val("floor")
        ref_price = get_col_val("refPrice")

        # Xác định trạng thái tăng / giảm
        icon = "🟡"
        if "-" in change:
            icon = "🔴"
        elif change != "0.00" and change != "N/A":
            icon = "🟢"

        return f"""📈 Cổ phiếu: {symbol_upper} (SSI iBoard HTML)
💵 Khớp lệnh: {matched_price} ({icon} {change} | {percent})
📊 Tổng KL: {volume} CP
🏷 Trần/Sàn/TC: {ceiling} / {floor} / {ref_price}"""

    except Exception as e:
        print("PARSE HTML ERROR:", e)
        return None

def get_stock_price(symbol: str):
    """
    Cào bảng giá từ iBoard:
    1. Ưu tiên fetch HTML trực tiếp từ nguồn bảng điện.
    2. Nếu HTML chưa được hydrate JS từ phía server, dùng endpoint dữ liệu của SSI iBoard để parse dữ liệu.
    """
    symbol = symbol.strip().upper()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://iboard.ssi.com.vn/"
    }

    try:
        # Thử lấy mã nguồn HTML của trang chủ bảng giá
        resp = requests.get("https://iboard.ssi.com.vn/", headers=headers, timeout=10)
        if resp.status_code == 200:
            parsed_result = parse_html_ssi_table(resp.text, symbol)
            if parsed_result:
                return parsed_result

        # Fallback: Vì iBoard render client-side qua React/AG-Grid, gọi qua data-feed của iBoard
        # để đảm bảo trả về đúng định dạng như các ô HTML trên bảng điện
        api_url = f"https://iboard-query.ssi.com.vn/stock/stock-detail?stockSymbol={symbol}"
        api_resp = requests.get(api_url, headers=headers, timeout=10)
        if api_resp.status_code == 200:
            data = api_resp.json().get("data", {})
            if data:
                cp = data.get("cp", 0)
                ch = data.get("ch", 0)
                chp = data.get("chp", 0)
                vol = data.get("vol", 0)
                ceil = data.get("ceil", 0)
                fl = data.get("fl", 0)
                ref = data.get("ref", 0)

                icon = "🟢" if ch > 0 else ("🔴" if ch < 0 else "🟡")
                sign = "+" if ch > 0 else ""

                return f"""📈 SSI iBoard: {symbol}
💵 Khớp lệnh: {cp:,.2f} ({icon} {sign}{ch:,.2f} | {sign}{chp:.2f}%)
📊 Tổng KL: {vol:,.0f} CP
🏷 Trần/Sàn/TC: {ceil:,.2f} / {fl:,.2f} / {ref:,.2f}"""

    except Exception as e:
        print("GET STOCK ERROR:", e)

    return f"❌ Không tìm thấy thông tin mã `{symbol}` trên bảng giá SSI iBoard."

# ================== TELEGRAM ==================
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message, 
        "👋 Chào bạn!\n"
        "- Gõ /gold để xem giá vàng & bạc\n"
        "- Gõ /token <mã> hoặc /stock <mã> để tra bảng giá SSI (Ví dụ: /token mbb)"
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
        bot.reply_to(message, "⚠️ Vui lòng nhập kèm mã cổ phiếu.\nVí dụ: `/token mbb` hoặc `/stock hpg`", parse_mode="Markdown")
        return

    symbol = parts[1]
    msg = bot.reply_to(message, f"⏳ Đang tra cứu mã `{symbol.upper()}`...", parse_mode="Markdown")

    result = get_stock_price(symbol)
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=msg.message_id,
        text=result
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
    bot.set_webhook(
        url="https://gold-coin-telebot.onrender.com/webhook"
    )
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
