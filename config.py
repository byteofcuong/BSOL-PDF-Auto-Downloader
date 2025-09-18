SECRET_KEY = '1312'
import os
#DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "OneDrive", "BSOL Downloads")
DOWNLOADS_PATH = os.path.join(os.path.expanduser('~'), 'Downloads')
DOWNLOAD_DIR = os.path.join(DOWNLOADS_PATH, 'BSOL Downloads')

PDF_DIR = os.path.join(DOWNLOAD_DIR, "PDFs")
DOWNLOADED_FILES_PATH = os.path.join(DOWNLOAD_DIR, "downloaded_files.txt")
CHECKSUMS_PATH = os.path.join(DOWNLOAD_DIR, "checksums.txt")

PROGRESS_PATH = os.path.join(DOWNLOAD_DIR, "progress.txt")

import sys
CHROME_PATH = os.environ.get("CHROME_PATH")
if not CHROME_PATH:
	if sys.platform.startswith("win"):
		# Sửa lại trường PC_Name
		CHROME_PATH = r"C:\\Users\\PC_Name\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"
	elif sys.platform == "darwin":
		CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
	else:
		CHROME_PATH = None