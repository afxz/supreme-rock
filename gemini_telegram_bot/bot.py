import asyncio
import logging
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import BOT_TOKEN, CHANNEL_ID, BOT_ADMIN_ID
from gemini_api import gemini_generate_content
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from content_generator import get_clean_gemini_post

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Default topic for Gemini posts
current_topic = "Latest advancements in Artificial Intelligence"

IST = pytz.timezone('Asia/Kolkata')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) == str(BOT_ADMIN_ID):
        await update.message.reply_text("Gemini Telegram Bot started! Use /help for commands.")
    else:
        await update.message.reply_text("You are not authorized to use this bot.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) == str(BOT_ADMIN_ID):
        help_text = (
            "<b>Gemini Bot Admin Commands:</b>\n"
            "/post - Generate and post content now\n"
            "/settopic &lt;topic&gt; - Change the topic for posts\n"
            "/topic - Show current topic\n"
            "/help - Show this help message\n"
        )
        await update.message.reply_text(help_text, parse_mode="HTML")

async def settopic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_topic
    if str(update.effective_user.id) == str(BOT_ADMIN_ID):
        if context.args:
            current_topic = " ".join(context.args)
            await update.message.reply_text(f"Topic updated to: <b>{current_topic}</b>", parse_mode="HTML")
        else:
            await update.message.reply_text("Usage: /settopic &lt;topic&gt;", parse_mode="HTML")

async def topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) == str(BOT_ADMIN_ID):
        await update.message.reply_text(f"Current topic: <b>{current_topic}</b>", parse_mode="HTML")

async def post(update: Update = None, context: ContextTypes.DEFAULT_TYPE = None, manual: bool = False):
    try:
        content = await get_clean_gemini_post(current_topic)
        # Post to channel
        bot = Bot(token=BOT_TOKEN)
        try:
            # Telegram message length limit
            MAX_LENGTH = 4096
            # Send in chunks if too long
            if len(content) > MAX_LENGTH:
                for i in range(0, len(content), MAX_LENGTH):
                    await bot.send_message(chat_id=CHANNEL_ID, text=content[i:i+MAX_LENGTH], parse_mode="HTML", disable_web_page_preview=False)
            else:
                await bot.send_message(chat_id=CHANNEL_ID, text=content, parse_mode="HTML", disable_web_page_preview=False)
        except Exception as e:
            # Fallback: strip all tags and try again
            import re
            plain = re.sub(r'<[^>]+>', '', content)
            await bot.send_message(chat_id=CHANNEL_ID, text=plain, parse_mode="HTML", disable_web_page_preview=False)
            if manual and update:
                await update.message.reply_text(f"Error: {e} (Fallback to plain text)")
            logger.error(f"Error posting to channel: {e} (Fallback to plain text)")
            return
        if manual and update:
            await update.message.reply_text("Post sent to channel.")
        logger.info(f"Posted to channel: {content[:60]}...")
    except Exception as e:
        logger.error(f"Error posting to channel: {e}")
        if manual and update:
            await update.message.reply_text(f"Error: {e}")

async def periodic_post():
    while True:
        await post()
        await asyncio.sleep(3600)  # Post every hour

async def scheduled_post():
    await post()

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settopic", settopic))
    application.add_handler(CommandHandler("topic", topic))
    application.add_handler(CommandHandler("post", lambda u, c: post(u, c, manual=True)))
    await application.initialize()
    await application.start()

    # APScheduler for scheduled posting
    scheduler = AsyncIOScheduler(timezone=IST)
    # Daily at 10:00 AM IST
    scheduler.add_job(scheduled_post, CronTrigger(hour=10, minute=0))
    # Example: Weekly on Monday at 9:00 AM IST
    # scheduler.add_job(scheduled_post, CronTrigger(day_of_week='mon', hour=9, minute=0))
    scheduler.start()

    await application.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
