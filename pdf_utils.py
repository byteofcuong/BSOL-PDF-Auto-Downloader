import os
import hashlib
from config import PDF_DIR, DOWNLOADED_FILES_PATH, CHECKSUMS_PATH, PROGRESS_PATH

def get_latest_pdf_filename():
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files:
        return None
    latest_file = max([os.path.join(PDF_DIR, f) for f in pdf_files], key=os.path.getctime)
    return os.path.basename(latest_file)

def get_pdf_checksum(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def read_downloaded_files():
    if os.path.exists(DOWNLOADED_FILES_PATH):
        with open(DOWNLOADED_FILES_PATH, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def write_downloaded_file(filename):
    with open(DOWNLOADED_FILES_PATH, "a", encoding="utf-8") as f:
        f.write(filename + "\n")

def read_checksums():
    if os.path.exists(CHECKSUMS_PATH):
        with open(CHECKSUMS_PATH, "r", encoding="utf-8") as f:
            return dict(line.strip().split("|", 1) for line in f if line.strip())
    return dict()

def write_checksum(checksum, filename):
    with open(CHECKSUMS_PATH, "a", encoding="utf-8") as f:
        f.write(f"{checksum}|{filename}\n")

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