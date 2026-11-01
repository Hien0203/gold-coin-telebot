
import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import Flask, Response, request
import telebot
from bs4 import BeautifulSoup

# ================== CONFIG ==================
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

URL_HAIHONG = "https://giavanghaihong.com/"
URL_MINHCHAU = "https://giavang.org/trong-nuoc/bao-tin-minh-chau/"
URL_SILVER = "https://giabac.net/"  # Hoặc trang web bạc bạn đang theo dõi

# ================== HTTP SESSION & RETRY CONFIG ==================
session_http = requests.Session()
retries = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504]
)
session_http.mount("https://", HTTPAdapter(max_retries=retries))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ================== HTML SCRAPING FUNCTIONS ==================

def fetch_html(url):
    try:
        res = session_http.get(url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            return res.text
    except Exception as e:
        print(f"FETCH HTML ERROR ({url}):", e)
    return None

def get_gold_world():
    # Có thể cào từ kitco hoặc một trang tin tức kinh tế khác
    return "🌍 Giá vàng thế giới: (Đang cập nhật nguồn mới)"

def get_haihong():
    html = fetch_html(URL_HAIHONG)
    if not html:
        return "❌ Không thể lấy dữ liệu Hải Hồng"
    
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="goldbox-table")
    if not table:
        return "❌ Không tìm thấy bảng giá Hải Hồng"

    result = ["🏪 Vàng Hải Hồng:"]
    rows = table.find_all("tr")[1:]  # Bỏ qua header
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 3:
            name = cols[0].text.strip()
            buy = cols[1].text.strip()
            sell = cols[2].text.strip()
            result.append(f"• {name}\n  Mua: {buy} | Bán: {sell}")
            
    return "\n".join(result) if len(result) > 1 else "❌ Bảng giá Hải Hồng trống"

def get_minhchau():
    html = fetch_html(URL_MINHCHAU)
    if not html:
        return "❌ Không thể lấy dữ liệu Bảo Tín Minh Châu"
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Tìm các ô chứa giá mua vào và bán ra dựa theo cấu trúc HTML bạn gửi
    buy_box = soup.find(lambda tag: tag.name == 'span' and 'Mua vào' in tag.text)
    sell_box = soup.find(lambda tag: tag.name == 'span' and 'Bán ra' in tag.text)
    
    buy_price = "N/A"
    sell_price = "N/A"
    
    if buy_box:
        parent_div = buy_box.find_parent('div', class_='box-cgre')
        if parent_div:
            price_span = parent_div.find('span', class_='gold-price')
            if price_span:
                # Lấy số tiền và loại bỏ khoảng trắng thừa
                buy_price = price_span.contents[0].strip()
                
    if sell_box:
        parent_div = sell_box.find_parent('div', class_='box-cred')
        if parent_div:
            price_span = parent_div.find('span', class_='gold-price')
            if price_span:
                sell_price = price_span.contents[0].strip()

    return f"""💎 Bảo Tín Minh Châu:
- Mua vào: {buy_price}k/lượng
- Bán ra: {sell_price}k/lượng"""

def get_silver():
    html = fetch_html(URL_SILVER)
    if not html:
        return "❌ Không thể lấy dữ liệu Giá Bạc"
    
    soup = BeautifulSoup(html, "html.parser")
    # Cấu trúc đọc bảng tùy thuộc vào trang web bạc bạn chọn
    table = soup.find("table")
    if not table:
        return "🥈 Giá Bạc: Đang cập nhật"
    
    result = ["🥈 Giá Bạc:"]
    rows = table.find_all("tr")[1:3]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 3:
            name = cols[0].text.strip()
            buy = cols[1].text.strip()
            sell = cols[2].text.strip()
            result.append(f"• {name}: Mua {buy} - Bán {sell}")
            
    return "\n".join(result)

# ================== STOCK FUNCTION (SSI IBOARD API) ==================
from bs4 import BeautifulSoup

# ================== STOCK FUNCTION (VIETSTOCK HTML SCRAPING) ==================
# ================== STOCK FUNCTION (TEST SHOW HTML) ==================
def get_stock_price(symbol: str):
    clean_symbol = symbol.strip().upper()
    url = "https://banggia.vietstock.vn/bang-gia/hose"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://banggia.vietstock.vn/"
    }

    try:
        res = session_http.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            return f"❌ Không thể tải trang bảng giá Vietstock (Mã lỗi: {res.status_code})."
        
        html_content = res.text
        
        # Telegram giới hạn 4096 ký tự cho mỗi tin nhắn, ta lấy 3000 ký tự đầu để test
        snippet = html_content[:3000]
        
        return f"""🔍 *DEBUG HTML (Từ khóa: `{clean_symbol}`)*
- Status Code: `{res.status_code}`
- Tổng độ dài HTML: `{len(html_content)}` ký tự
- Nội dung trích xuất (3000 ký tự đầu):

{snippet}"""

    except Exception as err:
        print(f"⚠️ Lỗi kết nối Vietstock: {err}")
        return f"❌ Lỗi khi cào dữ liệu: {err}"

# ================== TELEGRAM HANDLERS ==================
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "👋 Chào bạn!\n"
        "- Gõ /gold để xem giá vàng & bạc\n"
        "- Gõ /token <mã> hoặc /stock <mã> để tra bảng giá SSI (Ví dụ: `/token mbb`)"
    )

@bot.message_handler(commands=["gold"])
def gold(message):
    msg = bot.reply_to(message, "⏳ Đang cào dữ liệu từ các trang web...")
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
        bot.reply_to(message, "⚠️ Vui lòng nhập kèm mã cổ phiếu. Ví dụ: `/token mbb`", parse_mode="Markdown")
        return

    symbol = parts[1]
    msg = bot.reply_to(message, f"⏳ Đang lấy dữ liệu `{symbol.upper()}`...", parse_mode="Markdown")
    result = get_stock_price(symbol)
    bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=result, parse_mode="Markdown")

# ================== FLASK ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def home():
    try:
        with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        html = "<h1>Missing index.html</h1>"

    html = html.replace("{{world}}", get_gold_world())
    html = html.replace("{{haihong}}", get_haihong().replace("\n", "<br>"))
    html = html.replace("{{minhchau}}", get_minhchau().replace("\n", "<br>"))
    html = html.replace("{{silver}}", get_silver().replace("\n", "<br>"))
    mbb_data = get_stock_price("MBB").replace("\n", "<br>")
    html = html.replace("{{MBB}}", mbb_data)
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
#     print("🚀 Bot starting...")
#     bot.remove_webhook()
#     bot.set_webhook(url="https://gold-coin-telebot.onrender.com/webhook")
#     app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
