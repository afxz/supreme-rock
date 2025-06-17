import random
import secrets
import asyncio
import logging
from scrape_links import get_latest_canva_link
from config import CHANNEL_ID
from shared import format_canva_post_message, vote_data, last_posted_link, EMOJI_PAIRS

logger = logging.getLogger(__name__)

# Global auto-posting interval (in seconds)
auto_post_min = 900  # default 15 min
auto_post_max = 1800  # default 30 min

def set_auto_post_interval(min_sec, max_sec):
    global auto_post_min, auto_post_max
    auto_post_min = min_sec
    auto_post_max = max_sec
    logger.info(f"[auto_posting_task] Interval updated: {auto_post_min}-{auto_post_max} seconds")

async def auto_posting_task(bot):
    global last_posted_link
    import logging
    while True:
        try:
            # Store the interval range at the start
            start_min = auto_post_min
            start_max = auto_post_max
            sleep_time = random.randint(start_min, start_max)
            logging.info(f"[auto_posting_task] Next auto-post in {sleep_time} seconds (interval range: {start_min}-{start_max}).")
            for _ in range(sleep_time):
                await asyncio.sleep(1)
                # If interval changed, break and restart sleep with new interval
                if (auto_post_min, auto_post_max) != (start_min, start_max):
                    logging.info("[auto_posting_task] Interval changed during sleep, recalculating...")
                    break
            else:
                logging.info(f"[auto_posting_task] Woke up after {sleep_time} seconds. Checking for new link...")
                latest = await get_latest_canva_link()
                if latest is None:
                    logger.warning("[auto_posting_task] No link could be scraped (get_latest_canva_link returned None). Will retry after interval.")
                    continue
                if latest and latest != last_posted_link:
                    working_votes = 0
                    not_working_votes = 0
                    emoji_pair = secrets.choice(EMOJI_PAIRS)
                    msg, keyboard, emoji_pair = format_canva_post_message(latest, working_votes=working_votes, not_working_votes=not_working_votes, emoji_pair=emoji_pair)
                    sent_msg = await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="HTML", reply_markup=keyboard)
                    vote_data[sent_msg.message_id] = {'working': working_votes, 'not_working': not_working_votes, 'voters': set(), 'emoji_pair': emoji_pair}
                    last_posted_link = latest
                    logger.info(f"[auto_posting_task] Posted new link: {latest}")
                    # Delayed bump for auto-posts too
                    async def delayed_bump(msg_id, link, emoji_pair):
                        await asyncio.sleep(10)
                        bump_votes = random.randint(4, 6)
                        vote_data[msg_id]['working'] = bump_votes
                        msg, keyboard, _ = format_canva_post_message(link, working_votes=bump_votes, not_working_votes=0, emoji_pair=emoji_pair)
                        try:
                            await bot.edit_message_reply_markup(chat_id=CHANNEL_ID, message_id=msg_id, reply_markup=keyboard)
                        except Exception:
                            pass
                    asyncio.create_task(delayed_bump(sent_msg.message_id, latest, emoji_pair))
                else:
                    logger.info(f"[auto_posting_task] No new link found or already posted.")
        except Exception as e:
            logger.error(f"[auto_posting_task] Error: {e}")
