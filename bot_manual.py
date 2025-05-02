import asyncio
import logging
import sys
import platform
import random
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from scrape_links import get_latest_canva_link
from config import BOT_TOKEN, CHANNEL_ID, BOT_ADMIN_ID, IMPORTANT_LOG_PATH
from aiohttp import web
import os
import schedule
import pytz
from datetime import datetime, timedelta
from bot import post_latest_link

# Update logging configuration to write logs to a file
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Log auto-truncation on startup ---
LOG_FILES = ["bot.log", "important.log"]
MAX_LOG_LINES = 1000
for log_file in LOG_FILES:
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
        if len(lines) > MAX_LOG_LINES:
            with open(log_file, "w") as f:
                f.writelines(lines[-MAX_LOG_LINES:])
    except FileNotFoundError:
        pass

# Initialize the bot
bot = Bot(token=BOT_TOKEN)

# Store the last posted link
last_posted_link = None

# Helper to log important events
def log_important(event: str):
    with open(IMPORTANT_LOG_PATH, "a") as f:
        f.write(event + "\n")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BOT_ADMIN_ID:
        logger.info("/start command received from admin.")
        log_important(f"/start command by admin at {update.message.date}")
        await update.message.reply_text("Bot started successfully! Use /help to see available commands.")
    else:
        logger.warning("Unauthorized /start command attempt.")
        await update.message.reply_text("You are not authorized to use this command.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BOT_ADMIN_ID:
        help_text = (
            "<b>Admin Commands:</b>\n"
            "/post - Scrape and post the latest Canva link to the channel\n"
            "/lastlink - Show the last posted Canva link\n"
            "/logs - Show recent important logs (code style)\n"
            "/health - Check if the bot is running\n"
            "/restart - Restart the bot server\n"
            "/help - Show this help message\n"
        )
        await update.message.reply_text(help_text, parse_mode="HTML")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_posted_link
    if update.effective_user.id == BOT_ADMIN_ID:
        try:
            logger.info("/post command received from admin.")
            log_important(f"/post command by admin at {update.message.date}")
            # Add a small random delay to mimic human behavior
            await asyncio.sleep(random.uniform(1.0, 2.5))
            # Always call scraper with use_proxy=False to avoid 403 errors
            latest_link = await get_latest_canva_link(use_proxy=False)
            if latest_link and latest_link != last_posted_link:
                message = (
                    f"✅ <b>New Canva Link:</b>\n"
                    f"{latest_link}\n\n"
                    f"🔔 Unmute this channel to get access before others! ⏩\n"
                    f"⚡ <i>Powered by @CanvaProInviteLinks</i>"
                )
                await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode="HTML")
                await update.message.reply_text("Link posted to channel.")
                log_important(f"Posted new link at {update.message.date}: {latest_link}")
                last_posted_link = latest_link
            elif latest_link == last_posted_link:
                await update.message.reply_text("No new link found. The latest link is already posted.")
                log_important(f"No new link to post at {update.message.date}")
            else:
                await update.message.reply_text("Failed to fetch a valid Canva link.")
                log_important(f"Failed to fetch a valid Canva link at {update.message.date}")
        except Exception as e:
            logger.error(f"Error occurred while posting link: {e}")
            error_message = f"Error occurred while posting link: {e}"
            await bot.send_message(chat_id=BOT_ADMIN_ID, text=error_message)
            await update.message.reply_text("An error occurred. Check your DM for details.")
            log_important(f"ERROR at {update.message.date}: {e}")
    else:
        logger.warning("Unauthorized /post command attempt.")
        await update.message.reply_text("You are not authorized to use this command.")

async def lastlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BOT_ADMIN_ID:
        global last_posted_link
        msg = last_posted_link if last_posted_link else "No link posted yet."
        await update.message.reply_text(f"Last posted link: {msg}")
        log_important(f"/lastlink command by admin at {update.message.date}")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BOT_ADMIN_ID:
        try:
            with open(IMPORTANT_LOG_PATH, "r") as log_file:
                log_lines = log_file.readlines()
                recent_logs = "".join(log_lines[-20:])
                await bot.send_message(chat_id=BOT_ADMIN_ID, text=f"<code>{recent_logs}</code>", parse_mode="HTML")
                await update.message.reply_text("Recent important logs sent to your DM.")
        except Exception as e:
            logger.error(f"Error reading important logs: {e}")
            await bot.send_message(chat_id=BOT_ADMIN_ID, text=f"Error reading important logs: {e}")
            await update.message.reply_text("Failed to fetch important logs.")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BOT_ADMIN_ID:
        await update.message.reply_text("Bot is running and responsive.")
        log_important(f"/health command by admin at {update.message.date}")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BOT_ADMIN_ID:
        await update.message.reply_text("Restarting the bot server...")
        await bot.send_message(chat_id=BOT_ADMIN_ID, text="Bot is restarting as per your request.")
        log_important(f"/restart command by admin at {update.message.date}")
        os._exit(1)
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Improved health check endpoint
async def health_check(request):
    try:
        return web.Response(text="OK")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return web.Response(status=500, text="Health check failed")

async def root_check(request):
    return web.Response(text="OK")

async def start_health_check_server():
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_get("/", root_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

# Define IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Function to schedule posting at random times within given slots
def schedule_posting():
    def random_time_in_slot(start_hour, end_hour):
        start = datetime.now(IST).replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end = datetime.now(IST).replace(hour=end_hour, minute=0, second=0, microsecond=0)
        random_time = start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))
        return random_time

    # Schedule tasks for each slot
    slots = [
        (4, 6),  # 4 AM to 6 AM
        (9, 11), # 9 AM to 11 AM
        (13, 15), # 1 PM to 3 PM
        (18, 21), # 6 PM to 9 PM
        (0, 3)   # 12 AM to 3 AM
    ]

    for start_hour, end_hour in slots:
        post_time = random_time_in_slot(start_hour, end_hour)
        schedule.every().day.at(post_time.strftime('%H:%M')).do(asyncio.run, post_latest_link())

# Function to post the latest Canva link
async def post_latest_link():
    global last_posted_link
    try:
        logger.info("Checking for the latest Canva link...")
        latest_link = await get_latest_canva_link()
        if latest_link and latest_link != last_posted_link:
            logger.info(f"New link found: {latest_link}")
            message = (
                f"✅ <b>New Canva Link:</b>\n"
                f"{latest_link}\n\n"
                f"🔔 Unmute this channel to get access before others! ⏩\n"
                f"⚡ <i>Powered by @CanvaProInviteLinks</i>"
            )
            await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode="HTML")
            last_posted_link = latest_link
        else:
            logger.info("No new link found.")
    except Exception as e:
        logger.error(f"Error occurred while posting link: {e}")
        error_message = f"Error occurred while posting link: {e}"
        await bot.send_message(chat_id=BOT_ADMIN_ID, text=error_message)

# Optimized scheduling loop
async def optimized_schedule_runner():
    while True:
        schedule.run_pending()
        next_run = schedule.idle_seconds()
        if next_run is None:
            # No tasks scheduled, sleep for a default duration
            await asyncio.sleep(60)
        else:
            # Sleep until the next scheduled task
            await asyncio.sleep(next_run)

# Wrap main loop with error handling
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("post", post))
    application.add_handler(CommandHandler("lastlink", lastlink))
    application.add_handler(CommandHandler("logs", logs))
    application.add_handler(CommandHandler("health", health))
    application.add_handler(CommandHandler("restart", restart))

    # Initialize and start the application
    try:
        await application.initialize()
        await application.start()

        # Start the health check server
        health_check_task = asyncio.create_task(start_health_check_server())

        # Schedule posting tasks
        schedule_posting()

        # Run the optimized schedule runner
        schedule_task = asyncio.create_task(optimized_schedule_runner())

        logger.info("Bot is starting polling...")
        await asyncio.Event().wait()  # Keep the bot running indefinitely
    except Exception as e:
        logger.error(f"Critical error in main loop: {e}")
    finally:
        logger.info("Shutting down bot...")
        await application.updater.stop()
        await application.stop()
        health_check_task.cancel()
        schedule_task.cancel()
        try:
            await health_check_task
            await schedule_task
        except asyncio.CancelledError:
            pass
        await application.shutdown()

# Set event loop policy for compatibility
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    try:
        logger.info("Starting bot...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
