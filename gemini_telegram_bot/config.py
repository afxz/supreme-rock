import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gemini API keys (comma-separated)
GEMINI_API_KEYS = os.getenv("GEMINI_API_KEYS", "").split(",")

# Telegram bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Telegram channel ID
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Admin user ID (optional, for admin commands)
BOT_ADMIN_ID = os.getenv("BOT_ADMIN_ID")

def validate():
    if not GEMINI_API_KEYS or not GEMINI_API_KEYS[0]:
        raise ValueError("GEMINI_API_KEYS is not set.")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set.")
    if not CHANNEL_ID:
        raise ValueError("CHANNEL_ID is not set.")

validate()
