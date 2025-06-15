#!/usr/bin/env python3
import logging
import sys
import platform
import random
import os
import asyncio
from datetime import datetime, timedelta
import secrets
import json
import time

import pytz
from aiohttp import web
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

from scrape_links import get_latest_canva_link
from config import BOT_TOKEN, CHANNEL_ID, BOT_ADMIN_ID, IMPORTANT_LOG_PATH
from auto_posting import auto_posting_task
from shared import vote_data, last_posted_link, format_canva_post_message, EMOJI_PAIRS

import aiohttp
from bs4 import BeautifulSoup
from admin_commands import lastlink, logs, health, restart

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Truncate old logs on startup ---
for log_file in ("bot.log", IMPORTANT_LOG_PATH):
    try:
        lines = open(log_file, "r").read().splitlines()
        if len(lines) > 1000:
            open(log_file, "w").write("\n".join(lines[-1000:]) + "\n")
    except FileNotFoundError:
        pass

# --- Globals ---
bot = Bot(token=BOT_TOKEN)

def log_important(event: str):
    with open(IMPORTANT_LOG_PATH, "a") as f:
        f.write(event + "\n")

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    if user and user.id == BOT_ADMIN_ID:
        logger.info("/start command received.")
        if message and hasattr(message, 'date'):
            log_important(f"/start by admin at {message.date}")
        if message and hasattr(message, 'reply_text'):
            await message.reply_text("🎉 Bot started! Use /help to see commands.")
    else:
        if message and hasattr(message, 'reply_text'):
            await message.reply_text("🚫 You’re not authorized.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    if user and user.id == BOT_ADMIN_ID:
        txt = (
            "<b>Admin Commands:</b>\n"
            "/post - Scrape & post the latest link\n"
            "/help - This menu\n"
            "/lastlink - Show the last posted Canva link\n"
            "/logs - Show recent important logs\n"
            "/health - Check bot health\n"
            "/restart - Restart the bot (Koyeb will auto-restart)\n"
            "\n"
            "<b>Auto-Posting Info:</b>\n"
            "• The bot automatically checks for new Canva links every 40–50 minutes (randomized).\n"
            "• A new link is posted to the channel as soon as it is detected.\n"
            "• Scraping is now done via Scrape.do only, with multiple API keys supported.\n"
            "\n"
            "<b>Channel Post Format:</b>\n"
            "- Each post contains the Canva link, a proof/verification instruction, and two buttons: Share Channel and Join Backup.\n"
            "- Users can vote if the link is working or not using fun random emojis. Vote counts update live.\n"
            "- No backup channel button or repeated info.\n"
        )
        if message and hasattr(message, 'reply_text'):
            await message.reply_text(txt, parse_mode="HTML")
    else:
        if message and hasattr(message, 'reply_text'):
            await message.reply_text("🚫 Unauthorized.")

# --- Voting Callback Handler ---
import telegram
async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = getattr(update, 'callback_query', None)
    if not query or not hasattr(query, 'message') or not hasattr(query, 'from_user'):
        return
    user_id = getattr(query.from_user, 'id', None)
    msg = getattr(query, 'message', None)
    msg_id = getattr(msg, 'message_id', None)
    data = getattr(query, 'data', None)
    if msg_id is None or user_id is None or data is None:
        return
    # Parse emoji pair from callback_data
    parts = data.split('|')
    action = parts[0]
    good_emoji = parts[1] if len(parts) > 1 else "🟢"
    bad_emoji = parts[2] if len(parts) > 2 else "🔴"
    emoji_pair = (good_emoji, bad_emoji)
    # Initialize vote data if not present
    if msg_id not in vote_data:
        vote_data[msg_id] = {'working': 0, 'not_working': 0, 'voters': set(), 'emoji_pair': emoji_pair}
    votes = vote_data[msg_id]
    if 'emoji_pair' not in votes:
        votes['emoji_pair'] = emoji_pair
    if user_id in votes['voters']:
        try:
            await query.answer("You already voted on this link!", show_alert=True)
        except telegram.error.BadRequest as e:
            if "query is too old" in str(e).lower() or "query id is invalid" in str(e).lower():
                logger.warning(f"[vote_callback] Ignored old/invalid query: {e}")
            else:
                logger.error(f"[vote_callback] Unexpected error: {e}")
        return
    if action == "vote_working":
        votes['working'] += 1
        votes['voters'].add(user_id)
        try:
            await query.answer("Thanks for your feedback!", show_alert=False)
        except telegram.error.BadRequest as e:
            if "query is too old" in str(e).lower() or "query id is invalid" in str(e).lower():
                logger.warning(f"[vote_callback] Ignored old/invalid query: {e}")
            else:
                logger.error(f"[vote_callback] Unexpected error: {e}")
    elif action == "vote_not_working":
        votes['not_working'] += 1
        votes['voters'].add(user_id)
        try:
            await query.answer("We'll post a new link soon!", show_alert=True)
        except telegram.error.BadRequest as e:
            if "query is too old" in str(e).lower() or "query id is invalid" in str(e).lower():
                logger.warning(f"[vote_callback] Ignored old/invalid query: {e}")
            else:
                logger.error(f"[vote_callback] Unexpected error: {e}")
        try:
            await context.bot.send_message(chat_id=user_id, text="Thanks for reporting! Please wait for a new Canva link to be posted soon.")
        except Exception:
            pass
    # Extract the Canva link from the message text robustly
    canva_link = None
    msg_text = getattr(msg, 'text', None)
    if msg_text:
        lines = msg_text.split('\n')
        for line in lines:
            if line.startswith('https://www.canva.com/'):
                canva_link = line.strip()
                break
            if '<a href=' in line and 'canva.com' in line:
                import re
                m = re.search(r"<a href='([^']+canva.com[^']*)'", line)
                if m:
                    canva_link = m.group(1)
                    break
        if not canva_link and len(lines) > 1:
            canva_link = lines[1].strip()
    formatted_msg, keyboard, _ = format_canva_post_message(
        latest_link=canva_link or "[link hidden]",
        working_votes=votes['working'],
        not_working_votes=votes['not_working'],
        emoji_pair=votes['emoji_pair']
    )
    try:
        await query.edit_message_reply_markup(reply_markup=keyboard)
    except Exception:
        pass

# --- Patch posting logic to include voting ---
async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_posted_link
    user = update.effective_user
    message = update.message
    if not (user and user.id == BOT_ADMIN_ID):
        if message and hasattr(message, 'reply_text'):
            return await message.reply_text("🚫 Unauthorized.")
        return
    try_count = 0
    max_tries = 3
    latest = None
    error_msg = None
    while try_count < max_tries:
        try:
            if message and hasattr(message, 'date'):
                if try_count == 0:
                    log_important(f"/post at {message.date}")
            await asyncio.sleep(random.uniform(1, 2.5))
            latest = await get_latest_canva_link()
            if latest and latest != last_posted_link:
                working_votes = 0
                not_working_votes = 0
                emoji_pair = secrets.choice(EMOJI_PAIRS)
                msg, keyboard, _ = format_canva_post_message(latest, working_votes=working_votes, not_working_votes=not_working_votes, emoji_pair=emoji_pair)
                sent_msg = await context.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="HTML", reply_markup=keyboard)
                vote_data[sent_msg.message_id] = {'working': working_votes, 'not_working': not_working_votes, 'voters': set(), 'emoji_pair': emoji_pair}
                last_posted_link = latest
                if message and hasattr(message, 'reply_text'):
                    await message.reply_text("✅ Link posted.")
                log_important(f"Posted link: {latest}")
                # --- Delayed bump of working votes ---
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
                return
            elif latest == last_posted_link:
                if message and hasattr(message, 'reply_text'):
                    await message.reply_text("ℹ️ No new link.")
                log_important("No new link found.")
                return
            else:
                error_msg = "Fetch returned no valid link."
        except Exception as e:
            error_msg = str(e)
        try_count += 1
    if message and hasattr(message, 'reply_text'):
        await message.reply_text(f"❌ Could not fetch a new Canva link after {max_tries} tries. Last error: {error_msg}")
    logger.error(f"Error in /post after {max_tries} tries: {error_msg}")
    await context.bot.send_message(chat_id=BOT_ADMIN_ID, text=f"Error in /post after {max_tries} tries: {error_msg}")
    log_important(f"ERROR in /post after {max_tries} tries: {error_msg}")

# --- Health & Root Endpoints ---
async def health_check(request): return web.Response(text="OK")
async def root(request): return web.Response(text="Bot is up!")

async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_get("/", root)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Health server running on :8080")

# --- Register handlers in main() ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("post", post))
    app.add_handler(CommandHandler("lastlink", lastlink))
    app.add_handler(CommandHandler("logs", logs))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CallbackQueryHandler(vote_callback, pattern=r"^vote_"))
    # Start health server and auto-posting
    loop = asyncio.get_event_loop()
    loop.create_task(start_health_server())
    loop.create_task(auto_posting_task(app))
    logger.info("Starting polling…")
    app.run_polling()

if __name__ == "__main__":
    if platform.system() == "Windows" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(getattr(asyncio, "WindowsSelectorEventLoopPolicy")())
    main()
