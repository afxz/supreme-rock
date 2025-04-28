import time
import asyncio
from scrape_links import get_latest_canva_link
import logging
from telegram_bot import send_telegram_message
from config import CHANNEL_ID, ADMIN_GROUP_ID

logger = logging.getLogger()

last_checked_time = None
last_posted_link = None

async def check_links():
    global last_checked_time, last_posted_link

    while True:
        try:
            # Get the latest Canva link
            latest_link = get_latest_canva_link()
            last_checked_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

            # Check if the link is new
            if latest_link and latest_link != last_posted_link:
                # Post the link to the Telegram channel
                await send_telegram_message(
                    chat_id=CHANNEL_ID,
                    text=(
                        f"✅ <b>New Canva Link:</b>\n"
                        f"{latest_link}\n\n"
                        f"🔔 <i>Unmute this channel to get access before others!</i> ⏩\n\n"
                        f"⚡ <i>Powered by @CanvaProInviteLinks</i>"
                    )
                )
                logger.info(f"Posted new link: {latest_link}")

                # Update the last posted link
                last_posted_link = latest_link

            else:
                logger.info("No new link found or duplicate link detected.")

            # Wait before checking again
            await asyncio.sleep(300)  # Check every 5 minutes

        except Exception as e:
            error_message = f"Error: {e}"
            logger.error(error_message)
            await send_telegram_message(chat_id=ADMIN_GROUP_ID, text=error_message)
            await asyncio.sleep(60)  # Wait 1 minute before retrying