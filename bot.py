from telegram.ext import Application, CommandHandler
import time
import logging
from scrape_links import get_latest_canva_link
from config import BOT_TOKEN, CHANNEL_ID, ADMIN_ID

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

# Global variables to track bot status
last_checked_time = None
last_posted_link = None

def start(update, context):
    if update.effective_user.id == ADMIN_ID:
        update.message.reply_text("Bot is running and ready to post Canva links!")
    else:
        update.message.reply_text("You are not authorized to use this command.")

def status(update, context):
    if update.effective_user.id == ADMIN_ID:
        status_message = (
            f"Last Checked Time: {last_checked_time}\n"
            f"Last Posted Link: {last_posted_link if last_posted_link else 'No link posted yet.'}"
        )
        update.message.reply_text(status_message)
    else:
        update.message.reply_text("You are not authorized to use this command.")

def notify_admin(bot, message):
    try:
        bot.send_message(chat_id=ADMIN_ID, text=message)
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")

def main():
    global last_checked_time, last_posted_link

    # Initialize the bot application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))

    def check_links():
        global last_checked_time, last_posted_link

        while True:
            try:
                # Get the latest Canva link
                latest_link = get_latest_canva_link()
                last_checked_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

                # Check if the link is new
                if latest_link != last_posted_link:
                    # Post the link to the Telegram channel
                    application.bot.send_message(chat_id=CHANNEL_ID, text=f"✅ New Canva link: {latest_link}")
                    logger.info(f"Posted new link: {latest_link}")

                    # Update the last posted link
                    last_posted_link = latest_link

                # Wait before checking again
                time.sleep(300)  # Check every 5 minutes

            except Exception as e:
                error_message = f"Error: {e}"
                logger.error(error_message)
                application.bot.send_message(chat_id=ADMIN_ID, text=error_message)
                time.sleep(60)  # Wait 1 minute before retrying

    # Start the link-checking loop in a separate thread
    from threading import Thread
    Thread(target=check_links, daemon=True).start()

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()