import os
from config import PDF_DIR, DOWNLOADED_FILES_PATH, PROGRESS_PATH

def get_latest_pdf_filename():
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files:
        return None
    latest_file = max([os.path.join(PDF_DIR, f) for f in pdf_files], key=os.path.getctime)
    return os.path.basename(latest_file)

def read_downloaded_files():
    if os.path.exists(DOWNLOADED_FILES_PATH):
        with open(DOWNLOADED_FILES_PATH, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def write_downloaded_file(filename):
    with open(DOWNLOADED_FILES_PATH, "a", encoding="utf-8") as f:
        f.write(filename + "\n")

def read_progress():
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
            line = f.read().strip()
            if line:
                try:
                    page, idx = map(int, line.split("|"))
                    return page, idx
                except Exception:
                    pass
    return None, -1

def write_progress(page, idx):
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        f.write(f"{page}|{idx}\n")

def cut_filename(filename):
    name, ext = os.path.splitext(filename)
    if '--' in name:
        name = name.split('--', 1)[0].strip()
    return f"{name}{ext}" 