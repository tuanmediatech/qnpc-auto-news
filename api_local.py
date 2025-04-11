from flask import Flask, request, Response, stream_with_context
from playwright.sync_api import sync_playwright
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import os

app = Flask(__name__)

# Cấu hình Google Sheets
json_keyfile = "my-project-74363-183-3e2897feff9b.json"
spreadsheet_id = "19tnlgB7CXHMINIx1VSVkXQ--2sW9B5opyDOjjvU6S3g"

@app.route('/fetch', methods=["POST"])
def fetch_news():
    def generate_logs():
        try:
            num_articles = int(request.form.get("num_articles", 1))
            yield f"data: 📥 Yêu cầu lấy {num_articles} bài viết\n\n"

            yield "data: 🔄 Đang lấy danh sách bài viết...\n\n"
            articles = get_articles(num_articles)

            yield "data: 📝 Bắt đầu lấy nội dung từng bài viết...\n\n"
            news_list = []

            start = time.time()
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                for i, (title, link) in enumerate(articles):
                    yield f"data: 🔍 Đang xử lý bài {i+1}: {title}\n\n"
                    page.goto(link, timeout=60000)

                    try:
                        date = page.locator("#mvcContainer-11766 .heading-content p span").nth(0).inner_text()
                    except:
                        date = "Không có ngày"

                    content_locator = page.locator("#mvcContainer-11766 .article-content p").all()
                    content = " ".join([p.inner_text() for p in content_locator]) if content_locator else "Không có nội dung"

                    news_list.append([i+1, title, date, content, "", "Chờ duyệt", link])
                    time.sleep(0.3)

                browser.close()

            write_to_google_sheets(news_list)
            duration = round(time.time() - start, 2)

            yield "data: ✅ Ghi dữ liệu vào Google Sheets...\n\n"
            yield f"data: ✅ Hoàn tất! ⏱️ Mất {duration} giây.\n\n"
            yield "event: done\ndata: success\n\n"

        except Exception as e:
            yield f"data: ❌ Lỗi: {str(e)}\n\n"
            yield "event: done\ndata: failed\n\n"

    return Response(stream_with_context(generate_logs()), mimetype="text/event-stream")

def get_articles(num_articles):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://pcquangngai.cpc.vn", timeout=60000)
        page.wait_for_selector("#mvcContainer-12285")

        articles = page.locator("#mvcContainer-12285 a.title-link").all()
        data = [(a.inner_text(), a.get_attribute("href")) for a in articles[:num_articles]]

        browser.close()
        return data

def write_to_google_sheets(data):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(spreadsheet_id).sheet1
    sheet.clear()
    sheet.append_rows([["ID", "Tiêu đề", "Ngày đăng", "Nội dung", "Nội dung edit", "Trạng thái", "Link"]])
    sheet.append_rows(data)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5678)
