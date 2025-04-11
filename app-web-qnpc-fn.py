from flask import Flask, render_template, request, Response, stream_with_context
from playwright.sync_api import sync_playwright
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import os

app = Flask(__name__, template_folder="templates", static_folder="static")

# Load từ biến môi trường (Render hỗ trợ đặt qua Dashboard)
json_keyfile = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
spreadsheet_id = os.getenv("SPREADSHEET_ID", "your-spreadsheet-id")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/stream_logs', methods=["POST"])
def stream_logs():
    def generate_logs():
        try:
            num_articles = int(request.form.get("num_articles", 0))
            if num_articles <= 0:
                yield "data: ❌ Số lượng bài viết không hợp lệ.\n\n"
                yield "event: done\ndata: failed\n\n"
                return

            start_time = time.time()
            yield f"data: 📥 Yêu cầu lấy {num_articles} bài viết\n\n"
            yield "data: 🔄 Đang lấy danh sách bài viết...\n\n"

            articles = get_articles(num_articles)
            yield "data: 📝 Bắt đầu lấy nội dung từng bài viết...\n\n"

            news_list = []
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                for i, (title, link) in enumerate(articles):
                    yield f"data: 🔍 Đang xử lý bài {i+1}: {title}\n\n"
                    page.goto(link)

                    try:
                        date = page.locator("#mvcContainer-11766 .heading-content p span").nth(0).inner_text(timeout=60000)
                    except:
                        date = "Không có ngày"

                    content_locator = page.locator("#mvcContainer-11766 .article-content p").all()
                    content = " ".join([p.inner_text() for p in content_locator]) if content_locator else "Không có nội dung"

                    news_list.append([i+1, title, date, content, "", "Chờ duyệt", link])
                    time.sleep(0.3)

                browser.close()

            write_to_google_sheets(news_list)
            duration = round(time.time() - start_time, 2)
            yield f"data: ✅ Ghi dữ liệu vào Google Sheets...\n\n"
            yield f"data: ✅ Hoàn tất! ⏱️ Mất {duration} giây.\n\n"
            yield "event: done\ndata: success\n\n"

        except Exception as e:
            yield f"data: ❌ Lỗi: {str(e)}\n\n"
            yield "event: done\ndata: failed\n\n"

    return Response(stream_with_context(generate_logs()), mimetype='text/event-stream')

def get_articles(num_articles):
    print("🔗 Đang kiểm tra khả năng truy cập trang web...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://pcquangngai.cpc.vn", timeout=60000)
        page.wait_for_selector("#mvcContainer-12285")

        articles_locator = page.locator("#mvcContainer-12285").locator("a.title-link")
        articles = articles_locator.all()
        article_list = [(articles[i].inner_text(), articles[i].get_attribute("href")) for i in range(min(num_articles, len(articles)))]

        browser.close()
        return article_list

def write_to_google_sheets(data):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(spreadsheet_id).sheet1
    sheet.clear()
    sheet.append_rows([["ID", "Tiêu đề", "Ngày đăng", "Nội dung", "Nội dung edit", "Trạng thái", "Link"]])
    sheet.append_rows(data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
