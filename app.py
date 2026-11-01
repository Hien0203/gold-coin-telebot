
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

from bs4 import BeautifulSoup

# ================== STOCK FUNCTION (VIETSTOCK HTML PARSER) ==================
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
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Tìm thẻ tr chứa mã cổ phiếu dựa vào thuộc tính data-value của mã
        row = soup.find('tr', attrs={'data-value': clean_symbol})
        if not row:
            # Fallback tìm qua span nếu tr không khớp
            sym_tag = soup.find(lambda tag: tag.name == 'span' and tag.get('data-value') == clean_symbol and 'stock-symbol-s' in tag.get('class', []))
            if sym_tag:
                row = sym_tag.find_parent('tr')
                
        if not row:
            return f"❌ Không tìm thấy mã cổ phiếu `{clean_symbol}` trên bảng giá HOSE."
        
        # Lấy tên công ty từ tooltip
        company_name = clean_symbol
        tooltip = row.find('span', class_='tooltip-stock-name')
        if tooltip:
            company_name = tooltip.text.strip()
            
        # Tìm ID hậu tố của dòng (ví dụ: id kết thúc bằng -357)
        row_id_elem = row.find('span', id=lambda x: x and x.startswith('lastP-'))
        row_id = row_id_elem.get('id').split('-')[-1] if row_id_elem else None
        
        def get_val(prefix):
            if not row_id:
                return 0.0
            elem = row.find('span', id=f"{prefix}-{row_id}")
            if elem and elem.has_attr('data-value'):
                try:
                    val = elem['data-value']
                    if val == "undefined":
                        return 0.0
                    return float(val)
                except:
                    return 0.0
            return 0.0

        matched_price = get_val('lastP')
        change = get_val('lastC')
        percent = get_val('lastPC')
        volume = get_val('tVol')
        total_val = get_val('tVal')
        ceil_price = get_val('ceilP')
        floor_price = get_val('floorP')
        ref_price = get_val('basicP')
        high_price = get_val('highP')
        low_price = get_val('lowP')
        
        icon = "🟢" if change > 0 else ("🔴" if change < 0 else "🟡")
        sign = "+" if change > 0 else ""
        value_in_billion = total_val / 1_000_000_000 if total_val > 0 else (matched_price * volume) / 1_000_000_000

        return f"""📈 *{clean_symbol}* - {company_name}
💵 Giá khớp: *{matched_price:,.0f} VNĐ* ({icon} {sign}{change:,.0f} | {sign}{percent:.2f}%)
📊 Tổng KL: {volume:,.0f} CP (~{value_in_billion:,.2f} tỷ)
🏷 Trần/Sàn/TC: {ceil_price:,.0f} / {floor_price:,.0f} / {ref_price:,.0f}
↕️ Cao/Thấp: {high_price:,.0f} / {low_price:,.0f}"""

    except Exception as err:
        print(f"⚠️ Lỗi phân tích HTML Vietstock cho {clean_symbol}: {err}")
        return f"❌ Lỗi khi phân tích dữ liệu HTML cho mã `{clean_symbol}`."
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
