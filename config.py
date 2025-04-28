from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Telegram bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Telegram channel ID
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Admin group ID for bot control
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))