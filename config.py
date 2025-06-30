SECRET_KEY = '1312'
import os
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "OneDrive", "BSOL Downloads")
PDF_DIR = os.path.join(DOWNLOAD_DIR, "PDFs")
DOWNLOADED_FILES_PATH = os.path.join(DOWNLOAD_DIR, "downloaded_files.txt")
CHECKSUMS_PATH = os.path.join(DOWNLOAD_DIR, "checksums.txt")
PROGRESS_PATH = os.path.join(DOWNLOAD_DIR, "progress.txt") 