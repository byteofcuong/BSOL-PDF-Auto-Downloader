from flask import Flask, request, render_template, session
from pdf_utils import (
    read_downloaded_files, write_downloaded_file,
    read_progress, write_progress
)
from selenium_utils import get_current_page_number, handle_error_and_auth
from config import SECRET_KEY, PDF_DIR, DOWNLOAD_DIR
import os
import time
from selenium.webdriver.common.by import By
import openpyxl

app = Flask(__name__)
app.secret_key = SECRET_KEY

driver = None

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

EXCEL_PATH = os.path.join(DOWNLOAD_DIR, "List.xlsx")
if not os.path.exists(EXCEL_PATH):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Tên file", "Trạng thái", "Kết quả tải"])
    wb.save(EXCEL_PATH)

def append_to_excel(file_name, status, ket_qua=None):
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active
    ws.append([file_name, status, ket_qua if ket_qua is not None else ""])
    wb.save(EXCEL_PATH)

def strip_time_suffix(filename):
    if filename.endswith('.pdf'):
        base = filename[:-4]
        idx = base.rfind('--[')
        if idx != -1:
            return base[:idx] + '.pdf'
    return filename

def wait_for_pdf_download(before_files, pdf_dir, safe_file_name, timeout=30):
    import time, os
    start = time.time()
    while time.time() - start < timeout:
        after_files = set(f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf"))
        new_files = after_files - before_files
        if new_files:
            newest_file = max(new_files, key=lambda f: os.path.getctime(os.path.join(pdf_dir, f)))
            if strip_time_suffix(newest_file) == safe_file_name:
                time.sleep(3)
                return newest_file
        time.sleep(3)
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    global driver
    log = ""
    files_downloaded = 0

    log_file_path = os.path.join(DOWNLOAD_DIR, "log.txt")
    def write_log_to_file(msg):
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(msg)

    is_paused = os.path.exists("pause.flag")
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
            write_log_to_file(log)
            return render_template("index.html", log=log, files_downloaded=files_downloaded, is_paused=is_paused)

        elif action == "pause":
            with open("pause.flag", "w") as f:
                f.write("paused")
            log += "Đã tạm dừng quá trình tải. Bạn có thể tiếp tục bất cứ lúc nào.\n"
            write_log_to_file(log)
            is_paused = True
            return render_template("index.html", log=log, files_downloaded=files_downloaded, is_paused=is_paused)
        elif action == "resume":
            if os.path.exists("pause.flag"):
                os.remove("pause.flag")
            log += "Tiếp tục quá trình tải...\n"
            write_log_to_file(log)
            is_paused = False
            action = "download"
        elif action == "download":
            if driver is None:
                log += "Lỗi: Trình duyệt chưa được mở, hãy nhấn 'Bắt đầu' trước.\n"
                session['browser_started'] = False
                return render_template("index.html", log=log, files_downloaded=files_downloaded, is_paused=is_paused)
            while True:
                total_files = 0
                failed_files = 0
                downloaded_files = read_downloaded_files()
                last_page, last_block_idx = read_progress()
                if last_page is not None and last_page > 0:
                    current_page = get_current_page_number(driver, last_page)
                    while current_page < last_page:
                        try:
                            next_btn = driver.find_element(By.ID, "next-page")
                            if not next_btn.is_enabled() or 'disabled' in (next_btn.get_attribute("class") or "").lower():
                                log += "Không thể chuyển tiếp, đã đến trang cuối hoặc nút Next bị disable.\n"
                                break
                            next_btn.click()
                            for _ in range(30):
                                time.sleep(5)
                                new_page = get_current_page_number(driver, current_page)
                                if new_page != current_page:
                                    break
                            current_page = get_current_page_number(driver, current_page)
                        except Exception as e:
                            log += f"Lỗi khi chuyển trang tự động: {e}\n"
                            break
                reload_all = False
                while True:
                    if handle_error_and_auth(driver):
                        reload_all = True
                        break
                    
                    try:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                        driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(1)
                    except Exception:
                        pass
                    
                    if handle_error_and_auth(driver):
                        reload_all = True
                        break
                    
                    blocks = driver.find_elements(By.CSS_SELECTOR, "#searchResultContainer > li")
                    log += f"Tìm thấy {len(blocks)} blocks trên trang hiện tại.\n"
                    
                    if handle_error_and_auth(driver):
                        reload_all = True
                        break
                    
                    actual_doc_blocks = []
                    for i, block in enumerate(blocks):
                        try:
                            block.find_element(By.CSS_SELECTOR, "a.srch-result, a[href*='BibliographicInfoData']")
                            actual_doc_blocks.append((i, block))
                        except:
                            pass
                    
                    log += f"Trong đó có {len(actual_doc_blocks)} blocks chứa tài liệu thực sự.\n"
                    block_found = False
                    for original_idx, block in actual_doc_blocks:
                        idx = original_idx
                        while os.path.exists("pause.flag"):
                            log += "\nĐang tạm dừng..."
                            time.sleep(5)
                        current_page = get_current_page_number(driver, last_page)
                        if last_page == current_page and idx <= last_block_idx:
                            continue
                        block_found = True
                        try:
                            file_name = None
                            selectors = [
                                "a.srch-result",
                                ".srch-result", 
                                "a[href*='BibliographicInfoData']",
                                ".inner-search-result-list a"
                            ]
                            
                            for selector in selectors:
                                try:
                                    element = block.find_element(By.CSS_SELECTOR, selector)
                                    file_name = element.text.strip() + ".pdf"
                                    break
                                except:
                                    continue
                            
                            if not file_name:
                                log += f"Không tìm thấy tên file ở block {idx}, bỏ qua.\n"
                                continue
                                
                        except Exception as e:
                            log += f"Lỗi đọc tên file ở block {idx}: {e}, bỏ qua.\n"
                            continue
                        safe_file_name = file_name.replace("/", "-").replace("\\", "-").replace(":", "-").replace("*", "-").replace("?", "-").replace("\"", "'").replace("<", "(").replace(">", ")").replace("|", "-")
                        try:
                            status = ""
                            try:
                                status = block.find_element(By.CSS_SELECTOR, ".srch-rsl-subscribed, .srch-rsl-unsubscribed").text.strip()
                            except Exception:
                                pass
                            ket_qua = None
                            if status.lower().find("not in subscription") != -1:
                                ket_qua = "Không trong subscription"
                                append_to_excel(safe_file_name, status, ket_qua)
                            elif safe_file_name not in downloaded_files:
                                try:
                                    before_files = set(f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf") or f.lower().endswith(".crdownload"))
                                    
                                    btn = None
                                    btn_selectors = [
                                        "input.download-pdf",
                                        "input[value*='Download PDF']",
                                        ".download-pdf",
                                        "input[title*='Download PDF']"
                                    ]
                                    
                                    for btn_selector in btn_selectors:
                                        try:
                                            btn = block.find_element(By.CSS_SELECTOR, btn_selector)
                                            break
                                        except:
                                            continue
                                    
                                    if not btn:
                                        log += f"Không tìm thấy nút download cho {safe_file_name}.\n"
                                        ket_qua = "Không có nút download"
                                        append_to_excel(safe_file_name, status, ket_qua)
                                        continue
                                    if btn.is_enabled() and not btn.get_attribute("disabled"):
                                        btn.click()
                                        time.sleep(1)
                                        if handle_error_and_auth(driver):
                                            reload_all = True
                                            break
                                        pdf_file = wait_for_pdf_download(before_files, PDF_DIR, safe_file_name, timeout=60)
                                        if pdf_file:
                                            latest_path = os.path.join(PDF_DIR, pdf_file)
                                            new_path = os.path.join(PDF_DIR, safe_file_name)
                                            try:
                                                os.rename(latest_path, new_path)
                                                downloaded_files.add(safe_file_name)
                                                write_downloaded_file(safe_file_name)
                                                total_files += 1
                                                ket_qua = "Có"
                                                log += f"Đã tải thành công: {safe_file_name}\n"
                                            except Exception as e_rename:
                                                log += f"Không đổi tên được file {pdf_file} thành {safe_file_name}: {e_rename}\n"
                                                ket_qua = "Lỗi mạng"
                                        else:
                                            log += f"Không tải được file: {safe_file_name} (không tìm thấy file PDF mới phù hợp sau khi .crdownload biến mất)\n"
                                            ket_qua = "Lỗi mạng"
                                            failed_files += 1
                                        append_to_excel(safe_file_name, status, ket_qua)
                                    else:
                                        log += f"File {safe_file_name} không được phép tải (nút download bị disable).\n"
                                        ket_qua = "Không được phép tải"
                                        failed_files += 1
                                        append_to_excel(safe_file_name, status, ket_qua)
                                except Exception as e_btn:
                                    log += f"Không tìm thấy hoặc không click được nút download cho {safe_file_name}: {e_btn}\n"
                                    ket_qua = "Exception khi click nút"
                                    write_progress(last_page, idx - 5)
                                    if handle_error_and_auth(driver):
                                        reload_all = True
                                        break
                            else:
                                log += f"File {safe_file_name} đã tải trước đó, bỏ qua.\n"
                                ket_qua = "Có"
                                append_to_excel(safe_file_name, status, ket_qua)
                            current_page = get_current_page_number(driver, last_page)
                            write_progress(current_page, idx)
                        except Exception as e:
                            log += f"Lỗi không xác định với block: {e}\n"
                            append_to_excel(safe_file_name, "Lỗi không xác định", "Lỗi mạng")
                        if reload_all:
                            break
                    if reload_all:
                        break
                    if not block_found:
                        log += "Không còn block cha nào để tải trên trang này.\n"
                    try:
                        next_btn = driver.find_element(By.ID, "next-page")
                        if next_btn.is_enabled() and 'disabled' not in (next_btn.get_attribute("class") or "").lower():
                            next_btn.click()
                            time.sleep(5)
                            if handle_error_and_auth(driver):
                                reload_all = True
                                break
                            current_page = get_current_page_number(driver, last_page)
                            write_progress(current_page, -1)
                            last_page = current_page
                            last_block_idx = -1
                            log += "Chuyển sang trang tiếp theo...\n"
                            continue
                        else:
                            log += "Đã đến trang cuối, không còn trang nào để chuyển tiếp.\n"
                            break
                    except Exception as e:
                        log += f"Không tìm thấy nút Next Page hoặc đã đến trang cuối: {e}\n"
                        break
                if reload_all:
                    continue
                files_downloaded = total_files
                log += "Đã tải xong tất cả các file PDF!\n"
                write_log_to_file(log)
                write_progress(current_page, -1)
                return render_template("index.html", log=log, files_downloaded=files_downloaded, is_paused=is_paused)

    return render_template("index.html", log=log, files_downloaded=files_downloaded, is_paused=is_paused)

if __name__ == "__main__":
    app.run(debug=True)
