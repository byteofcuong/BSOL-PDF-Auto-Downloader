import os
import time
from flask import Flask, request, render_template, session, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

app = Flask(__name__)
app.secret_key = '1312'  # Đặt chuỗi bất kỳ, cần cho session

DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "BSOL Downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Selenium driver khai báo ngoài để giữ sống giữa các lần submit
driver = None

@app.route("/", methods=["GET", "POST"])
def index():
    global driver
    log = ""
    files_downloaded = 0
    success_rate = "100%"
    failed_files_list = []

    if request.method == "GET":
        session['browser_started'] = False

    if request.method == "POST":
        action = request.form.get("action", "")

        # 1. Nếu bấm nút "Bắt đầu", mở trình duyệt và lưu trạng thái vào session
        if action == "start_browser":
            options = Options()
            options.binary_location = r"C:\\Users\\Laptop Lenovo\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"
            #options.add_argument(r'--user-data-dir=C:\\Users\\Laptop Lenovo\\AppData\\Local\\Google\\Chrome\\User Data')
            #options.add_argument('--profile-directory=Profile 2')
            prefs = {
                "download.default_directory": DOWNLOAD_DIR,
                "download.prompt_for_download": False,
                "plugins.always_open_pdf_externally": True
            }
            options.add_experimental_option("prefs", prefs)
            driver = webdriver.Chrome(options=options)
            driver.get("https://bsol-bsigroup-com.ap1.proxy.openathens.net/")
            session['browser_started'] = True
            log += "Trình duyệt đã mở. Hãy tự login và thao tác đến đúng trang tài liệu bạn muốn tải.\n"
            log += "Khi đã ở đúng trang, quay lại đây và bấm 'Bắt đầu tải file PDF trên trang hiện tại'!"
            return render_template("index.html", log=log, files_downloaded=files_downloaded, success_rate=success_rate, failed_files_list=failed_files_list)
        
        # 2. Nếu bấm nút tải, bắt đầu thao tác auto trên trang hiện tại
        elif action == "download":
            if driver is None:
                log += "Lỗi: Trình duyệt chưa được mở, hãy nhấn 'Bắt đầu' trước.\n"
                session['browser_started'] = False
                return render_template("index.html", log=log, files_downloaded=files_downloaded, success_rate=success_rate, failed_files_list=failed_files_list)
            page_count = 1
            total_files = 0
            failed_files = 0
            failed_files_list = []
            while True:
                log += f"Trang {page_count}: Đang tải các file PDF...\n"
                try:
                    # Đợi nút download PDF xuất hiện
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input.download-pdf"))
                    )
                except TimeoutException:
                    log += "Không tìm thấy nút tải PDF trên trang này. Hãy chắc chắn bạn đang ở đúng trang tài liệu!\n"
                    break
                pdf_buttons = driver.find_elements(By.CSS_SELECTOR, "input.download-pdf")
                for idx, btn in enumerate(pdf_buttons, 1):
                    try:
                        btn.click()
                        time.sleep(1)
                        total_files += 1
                    except Exception as e:
                        log += f"Không click được một nút download: {e}\n"
                        failed_files += 1
                        failed_files_list.append(f"PDF_{idx}.pdf")
                try:
                    next_btn = driver.find_element(By.ID, "next-page")
                    if not next_btn.is_enabled() or 'disabled' in (next_btn.get_attribute("class") or "").lower():
                        log += "Đã đến trang cuối.\n"
                        break
                    next_btn.click()
                    # Đợi trang mới tải xong
                    try:
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input.download-pdf"))
                        )
                    except TimeoutException:
                        log += "Không tìm thấy nút tải PDF trên trang mới. Hãy chắc chắn bạn đang ở đúng trang tài liệu!\n"
                        break
                    time.sleep(1)
                    page_count += 1
                except Exception as e:
                    log += "Không tìm thấy nút Next Page hoặc đã đến trang cuối.\n"
                    break
            files_downloaded = total_files
            if total_files > 0:
                success_rate = f"{int(100 * (total_files - failed_files) / total_files)}%"
            else:
                success_rate = "0%"
            log += "Đã tải xong tất cả các file PDF!\n"
            return render_template("index.html", log=log, files_downloaded=files_downloaded, success_rate=success_rate, failed_files_list=failed_files_list)

    # GET hoặc chưa thao tác gì
    return render_template("index.html", log=log, files_downloaded=files_downloaded, success_rate=success_rate, failed_files_list=failed_files_list)

if __name__ == "__main__":
    app.run(debug=True)
