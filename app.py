from flask import Flask, request, render_template, session
from pdf_utils import (
    get_latest_pdf_filename, read_downloaded_files, write_downloaded_file,
    read_progress, write_progress, cut_filename
)
from selenium_utils import get_pdf_buttons_hash, get_current_page_number
from config import SECRET_KEY, PDF_DIR, DOWNLOADED_FILES_PATH, PROGRESS_PATH, DOWNLOAD_DIR
import os
import time
import random

app = Flask(__name__)
app.secret_key = SECRET_KEY

driver = None

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

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

        if action == "start_browser":
            from selenium_utils import create_driver
            driver = create_driver()
            session['browser_started'] = True
            log += "Trình duyệt đã mở. Hãy tự login và thao tác đến đúng trang tài liệu bạn muốn tải.\n"
            log += "Khi đã ở đúng trang, quay lại đây và bấm 'Bắt đầu tải file PDF trên trang hiện tại'!"
            return render_template("index.html", log=log, files_downloaded=files_downloaded, success_rate=success_rate, failed_files_list=failed_files_list)

        elif action == "download":
            if driver is None:
                log += "Lỗi: Trình duyệt chưa được mở, hãy nhấn 'Bắt đầu' trước.\n"
                session['browser_started'] = False
                return render_template("index.html", log=log, files_downloaded=files_downloaded, success_rate=success_rate, failed_files_list=failed_files_list)
            page_count = 1
            total_files = 0
            failed_files = 0
            failed_files_list = []
            downloaded_files = read_downloaded_files()
            last_page, last_index = read_progress()
            if last_page is not None and last_page > 0:
                current_page = get_current_page_number(driver)
                while current_page < last_page:
                    try:
                        next_btn = driver.find_element(By.ID, "next-page")
                        if not next_btn.is_enabled() or 'disabled' in (next_btn.get_attribute("class") or "").lower():
                            log += "Không thể chuyển tiếp, đã đến trang cuối hoặc nút Next bị disable.\n"
                            break
                        next_btn.click()
                        for _ in range(30):
                            time.sleep(5)
                            new_page = get_current_page_number(driver)
                            if new_page != current_page:
                                break
                        current_page = get_current_page_number(driver)
                    except Exception as e:
                        log += f"Lỗi khi chuyển trang tự động: {e}\n"
                        break
            while True:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.by import By
                from selenium.common.exceptions import TimeoutException
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input.download-pdf"))
                    )
                except TimeoutException:
                    log += "Không tìm thấy nút tải PDF trên trang này. Hãy chắc chắn bạn đang ở đúng trang tài liệu!\n"
                    break
                current_hash = get_pdf_buttons_hash(driver)
                current_page = get_current_page_number(driver)
                start_idx = 0
                log += f"\n=== Bắt đầu tải trang {current_page} ===\n"
                page_success = 0
                page_failed = 0
                if last_page == current_page and last_index >= 0:
                    start_idx = last_index + 1
                    log += f"Tiếp tục tải từ file số {start_idx+1} trên trang {current_page}.\n"
                else:
                    log += f"Bắt đầu tải từ file đầu tiên trên trang {current_page}.\n"
                pdf_buttons = driver.find_elements(By.CSS_SELECTOR, "input.download-pdf")
                for idx, btn in enumerate(pdf_buttons, 0):
                    if idx < start_idx:
                        continue
                    try:
                        btn.click()
                        delay = random.randint(10, 20)
                        time.sleep(delay)
                        latest_file = get_latest_pdf_filename()
                        if latest_file:
                            logic_file = cut_filename(latest_file)
                            latest_path = os.path.join(PDF_DIR, latest_file)
                            if logic_file not in downloaded_files:
                                downloaded_files.add(logic_file)
                                write_downloaded_file(logic_file)
                                total_files += 1
                                page_success += 1
                                log += f"Đã tải thành công: {logic_file}\n"
                            else:
                                log += f"File gốc: {logic_file} đã tải trước đó, bỏ qua.\n"
                                try:
                                    os.remove(latest_path)
                                except Exception as e_rm:
                                    log += f"Không xóa được file trùng: {logic_file}, lỗi: {e_rm}\n"
                        else:
                            log += f"Không xác định được tên file PDF vừa tải.\n"
                        write_progress(current_page, idx)
                    except Exception as e:
                        log += f"Không click được một nút download: {e}\n"
                        failed_files += 1
                        page_failed += 1
                log += f"Tổng kết trang {current_page}: {page_success} file thành công, {page_failed} file lỗi.\n"
                try:
                    next_btn = driver.find_element(By.ID, "next-page")
                    if not next_btn.is_enabled() or 'disabled' in (next_btn.get_attribute("class") or "").lower():
                        log += "Đã đến trang cuối.\n"
                        break
                    prev_hash = current_hash
                    next_btn.click()
                    for _ in range(30):
                        time.sleep(1)
                        try:
                            new_hash = get_pdf_buttons_hash(driver)
                            if new_hash != prev_hash:
                                break
                        except Exception:
                            pass
                    else:
                        log += "Chuyển trang không thành công hoặc trang mới không load được file PDF!\n"
                        break
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

    return render_template("index.html", log=log, files_downloaded=files_downloaded, success_rate=success_rate, failed_files_list=failed_files_list)

if __name__ == "__main__":
    app.run(debug=True)
