import random
import secrets
import asyncio
import logging
from scrape_links import get_latest_canva_link
from config import CHANNEL_ID
from shared import format_canva_post_message, vote_data, last_posted_link, EMOJI_PAIRS

logger = logging.getLogger(__name__)

async def auto_posting_task(context):
    global last_posted_link
    while True:
        try:
            await asyncio.sleep(random.randint(2400, 3000))  # 40–50 min
            latest = await get_latest_canva_link()
            if latest and latest != last_posted_link:
                working_votes = 0
                not_working_votes = 0
                emoji_pair = secrets.choice(EMOJI_PAIRS)
                msg, keyboard, emoji_pair = format_canva_post_message(latest, working_votes=working_votes, not_working_votes=not_working_votes, emoji_pair=emoji_pair)
                sent_msg = await context.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="HTML", reply_markup=keyboard)
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
                        await context.bot.edit_message_reply_markup(chat_id=CHANNEL_ID, message_id=msg_id, reply_markup=keyboard)
                    except Exception:
                        pass
                asyncio.create_task(delayed_bump(sent_msg.message_id, latest, emoji_pair))
        except Exception as e:
            logger.error(f"[auto_posting_task] Error: {e}")
