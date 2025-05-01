import asyncio
import logging
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from scrape_links import get_latest_canva_link
from config import BOT_TOKEN, CHANNEL_ID, BOT_ADMIN_ID
from aiohttp import web
import os

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

# Initialize the bot
bot = Bot(token=BOT_TOKEN)

# Store the last posted link
last_posted_link = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BOT_ADMIN_ID:
        logger.info("/start command received from admin.")
        await update.message.reply_text("Bot started successfully!")
    else:
        logger.warning("Unauthorized /start command attempt.")
        await update.message.reply_text("You are not authorized to use this command.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BOT_ADMIN_ID:
        global last_posted_link
        logger.info("/status command received from admin.")
        status_message = f"Last posted link: {last_posted_link if last_posted_link else 'No link posted yet.'}"
        await update.message.reply_text(status_message)
    else:
        logger.warning("Unauthorized /status command attempt.")
        await update.message.reply_text("You are not authorized to use this command.")

# Function to restart the bot server
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BOT_ADMIN_ID:
        logger.info("/restart command received from admin.")
        await update.message.reply_text("Restarting the bot server...")
        os._exit(1)  # Exit the process to trigger a restart
    else:
        logger.warning("Unauthorized /restart command attempt.")
        await update.message.reply_text("You are not authorized to use this command.")

# Function to fetch recent logs
async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BOT_ADMIN_ID:
        logger.info("/logs command received from admin.")
        try:
            with open("bot.log", "r") as log_file:
                log_lines = log_file.readlines()
                recent_logs = "\n".join(log_lines[-20:])  # Fetch the last 20 lines
                await update.message.reply_text(f"Recent Logs:\n{recent_logs}")
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            await update.message.reply_text("Failed to fetch logs.")
    else:
        logger.warning("Unauthorized /logs command attempt.")
        await update.message.reply_text("You are not authorized to use this command.")

async def post_latest_link():
    global last_posted_link
    while True:
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
        except asyncio.CancelledError:
            logger.info("Link posting task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error occurred while posting link: {e}")
            error_message = f"Error occurred while posting link: {e}"
            await bot.send_message(chat_id=BOT_ADMIN_ID, text=error_message)
        await asyncio.sleep(300)  # Check every 5 minutes

# Add a simple HTTP server for health checks
async def health_check(request):
    return web.Response(text="OK")

async def start_health_check_server():
    app = web.Application()
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(CommandHandler("logs", logs))

    # Initialize and start the application
    await application.initialize()
    await application.start()

    # Start the health check server
    health_check_task = asyncio.create_task(start_health_check_server())

    # Run the link posting loop in the background
    link_task = asyncio.create_task(post_latest_link())

    try:
        logger.info("Bot is starting polling...")
        await application.updater.start_polling()
        # Keep the bot running indefinitely
        await asyncio.Event().wait()
    finally:
        logger.info("Shutting down bot...")
        # Stop the updater explicitly before shutting down
        await application.updater.stop()
        await application.stop()
        link_task.cancel()
        health_check_task.cancel()
        try:
            await link_task
            await health_check_task
        except asyncio.CancelledError:
            pass
        await application.shutdown()

if __name__ == "__main__":
    try:
        logger.info("Starting bot...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
