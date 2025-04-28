import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Validate environment variables
def validate_env_var(var_name):
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Environment variable {var_name} is not set.")
    return value

# Telegram bot token
BOT_TOKEN = validate_env_var("BOT_TOKEN")

# Telegram channel ID
CHANNEL_ID = validate_env_var("CHANNEL_ID")

# Admin group ID for bot control
ADMIN_GROUP_ID = int(validate_env_var("ADMIN_GROUP_ID"))