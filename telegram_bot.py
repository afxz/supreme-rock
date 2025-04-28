from telegram.ext import Application, CommandHandler
import logging
from config import BOT_TOKEN, ADMIN_GROUP_ID
from shared_state import last_checked_time, last_posted_link

logger = logging.getLogger()

def create_bot_application():
    return Application.builder().token(BOT_TOKEN).build()

async def send_telegram_message(chat_id, text):
    try:
        application = create_bot_application()
        await application.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to send message: {e}")

async def start(update, context):
    if update.effective_chat.id == ADMIN_GROUP_ID:
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="Bot is running and ready to post Canva links!")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="This command is restricted to the admin group.")

async def status(update, context):
    if update.effective_chat.id == ADMIN_GROUP_ID:
        status_message = (
            f"Last Checked Time: {last_checked_time}\n"
            f"Last Posted Link: {last_posted_link if last_posted_link else 'No link posted yet.'}"
        )
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=status_message)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="This command is restricted to the admin group.")