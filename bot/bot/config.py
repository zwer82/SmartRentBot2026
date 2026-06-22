import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Webhook (Railway)
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "")        # e.g. https://myapp.up.railway.app
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else ""
PORT = int(os.getenv("PORT", 8080))

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json"
)
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
APPLICATIONS_SHEET_NAME = os.getenv("APPLICATIONS_SHEET_NAME", "Applications")
OBJECTS_SHEET_NAME = os.getenv("OBJECTS_SHEET_NAME", "Objects")

# Admins (comma-separated IDs)
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# Photos
PHOTOS_DIR = os.getenv("PHOTOS_DIR", "photos")
