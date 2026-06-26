import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

BASE_DIR = Path(__file__).parent.parent
WATCH_FOLDER = BASE_DIR / "watch_folder"
PROCESSED_FOLDER = WATCH_FOLDER / "processed"
DB_PATH = BASE_DIR / "reminders.db"

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "")
EMPLOYEE_EMAIL = os.getenv("EMPLOYEE_EMAIL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

AUDIO_EXTENSIONS = {".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".opus", ".webm", ".aac", ".flac"}
