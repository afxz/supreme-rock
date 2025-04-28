import time
import logging
from telegram import Bot
from scrape_links import get_latest_canva_link
from config import BOT_TOKEN, CHANNEL_ID

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

def main():
    bot = Bot(token=BOT_TOKEN)
    last_posted_link = None

    while True:
        try:
            # Get the latest Canva link
            latest_link = get_latest_canva_link()

            # Check if the link is new
            if latest_link != last_posted_link:
                # Post the link to the Telegram channel
                bot.send_message(chat_id=CHANNEL_ID, text=f"✅ New Canva link: {latest_link}")
                logger.info(f"Posted new link: {latest_link}")

                # Update the last posted link
                last_posted_link = latest_link

            # Wait before checking again
            time.sleep(300)  # Check every 5 minutes

        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    main()