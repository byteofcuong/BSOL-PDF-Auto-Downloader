from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import re
from config import PDF_DIR

def create_driver():
    options = Options()
    options.binary_location = r"C:\\Users\\Laptop Lenovo\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"
    prefs = {
        "download.default_directory": PDF_DIR,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=options)
    driver.get("https://bsol-bsigroup-com.ap1.proxy.openathens.net/")
    return driver

def get_pdf_buttons_hash(driver):
    pdf_buttons = driver.find_elements(By.CSS_SELECTOR, "input.download-pdf")
    return hash(tuple([btn.get_attribute('outerHTML') for btn in pdf_buttons]))

def get_current_page_number(driver):
    try:
        el = driver.find_element(By.CSS_SELECTOR, "span.num-page")
        return int(el.text)
    except Exception:
        return 1 