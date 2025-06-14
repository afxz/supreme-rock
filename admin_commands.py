import logging
from telegram import Update
from config import BOT_ADMIN_ID, IMPORTANT_LOG_PATH

logger = logging.getLogger(__name__)

def log_important(event: str):
    with open(IMPORTANT_LOG_PATH, "a") as f:
        f.write(event + "\n")

async def lastlink(update: Update, context):
    message = update.message
    if not message or not hasattr(message, 'reply_text'):
        return
    user = update.effective_user
    from bot import last_posted_link
    if user and user.id == BOT_ADMIN_ID:
        if last_posted_link:
            await message.reply_text(f"Last posted link: {last_posted_link}")
        else:
            await message.reply_text("No link has been posted yet.")
    else:
        await message.reply_text("🚫 Unauthorized.")

async def logs(update: Update, context):
    message = update.message
    if not message or not hasattr(message, 'reply_text'):
        return
    user = update.effective_user
    if user and user.id == BOT_ADMIN_ID:
        try:
            with open(IMPORTANT_LOG_PATH, "r") as f:
                lines = f.readlines()[-20:]
            await message.reply_text("Recent important logs:\n" + "".join(lines))
        except Exception as e:
            await message.reply_text(f"Error reading logs: {e}")
    else:
        await message.reply_text("🚫 Unauthorized.")

async def health(update: Update, context):
    message = update.message
    if not message or not hasattr(message, 'reply_text'):
        return
    user = update.effective_user
    if user and user.id == BOT_ADMIN_ID:
        await message.reply_text("Bot is healthy!")
    else:
        await message.reply_text("🚫 Unauthorized.")

async def restart(update: Update, context):
    message = update.message
    if not message or not hasattr(message, 'reply_text'):
        return
    user = update.effective_user
    if user and user.id == BOT_ADMIN_ID:
        await message.reply_text("Restarting bot...")
        import os
        os._exit(0)
    else:
        await message.reply_text("🚫 Unauthorized.")
