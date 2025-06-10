#!/usr/bin/env python3
import logging
import sys
import platform
import random
import os
import asyncio
from datetime import datetime, timedelta
import secrets

import pytz
from aiohttp import web
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

from scrape_links import get_latest_canva_link
from config import BOT_TOKEN, CHANNEL_ID, BOT_ADMIN_ID, IMPORTANT_LOG_PATH

import aiohttp
from bs4 import BeautifulSoup

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
last_posted_link = None

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
            "/lastlink - Show last posted link\n"
            "/logs - DM recent important logs\n"
            "/health - Check bot health\n"
            "/restart - Restart bot\n"
            "/help - This menu\n\n"
            "<b>Auto-Posting Info:</b>\n"
            "• The bot automatically checks for new Canva links every 5–10 minutes (randomized).\n"
            "• A new link is posted to the channel as soon as it is detected.\n"
            "• Scraping uses a smart proxy pool to avoid bans and maximize reliability.\n\n"
            "<b>Channel Post Format:</b>\n"
            "- Each post contains the Canva link, a proof/verification instruction, and two buttons: Share Channel and Send Proof.\n"
            "- Users can vote if the link is working or not using fun random emojis. Vote counts update live.\n"
            "- No backup channel button or repeated info.\n"
        )
        if message and hasattr(message, 'reply_text'):
            await message.reply_text(txt, parse_mode="HTML")
    else:
        if message and hasattr(message, 'reply_text'):
            await message.reply_text("🚫 Unauthorized.")

# --- Voting Data ---
vote_data = {}  # message_id: {'working': int, 'not_working': int, 'voters': set}

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

# --- Enhanced Message Formatting with Voting ---
def format_canva_post_message(latest_link, working_votes=None, not_working_votes=None, emoji_pair=None):
    import secrets
    emoji_pairs = [
        ("🟢", "🔴"), ("✅", "❌"), ("🔥", "😞"), ("💯", "😵"), ("😎", "😭"), ("🚀", "🛑"), ("🌟", "👎"), ("🥇", "🥀"), ("🍀", "🪦"), ("🎉", "😬")
    ]
    if emoji_pair is None:
        emoji_pair = secrets.choice(emoji_pairs)
    good_emoji, bad_emoji = emoji_pair
    # 🎯 Goal line
    goal_num = random.randint(4, 10)
    msg = (
        f"{good_emoji} <b>New Canva Pro Team Link:</b>\n"
        f"<a href='{latest_link}'>{latest_link}</a>\n\n"
        "🔔 <i>Unmute for instant access!</i>\n"
        "🖼️ <b>Proof:</b> After joining, send a screenshot to <a href='https://t.me/aenzBot'>@aenzBot</a>.\n\n"
        f"🎯 <b>Goal:</b> Let's hit <b>{goal_num}</b> reactions! 🚀\n"
        "<code>React below to help others know if it works!</code>"
    )
    if working_votes is None:
        working_votes = 0  # Start at 0, will be bumped after delay
    if not_working_votes is None:
        not_working_votes = 0
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{good_emoji} Working ({working_votes})", callback_data=f"vote_working|{good_emoji}|{bad_emoji}"),
            InlineKeyboardButton(f"{bad_emoji} Not Working ({not_working_votes})", callback_data=f"vote_not_working|{good_emoji}|{bad_emoji}")
        ],
        [
            InlineKeyboardButton("📣 Share Channel", url="https://t.me/share/url?url=https://t.me/CanvaProInviteLinks&text=Unlock daily Canva Pro team links! Totally free, always fresh."),
            InlineKeyboardButton("Join Backup ⚠️", url="https://t.me/+ejp2_sjBtJczY2I9")
        ]
    ])
    return msg, keyboard, emoji_pair

# --- Voting Callback Handler ---
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
        await query.answer("You already voted on this link!", show_alert=True)
        return
    if action == "vote_working":
        votes['working'] += 1
        votes['voters'].add(user_id)
        await query.answer("Thanks for your feedback!", show_alert=False)
    elif action == "vote_not_working":
        votes['not_working'] += 1
        votes['voters'].add(user_id)
        await query.answer("We'll post a new link soon!", show_alert=True)
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
            latest = await get_latest_canva_link(use_proxy=False)
            if latest and latest != last_posted_link:
                working_votes = 0
                not_working_votes = 0
                emoji_pairs = [
                    ("🟢", "🔴"), ("✅", "❌"), ("🔥", "😞"), ("💯", "😵"), ("😎", "😭"), ("🚀", "🛑"), ("🌟", "👎"), ("🥇", "🥀"), ("🍀", "🪦"), ("🎉", "😬")
                ]
                emoji_pair = secrets.choice(emoji_pairs)
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
        await message.reply_text("❌ Could not fetch a new Canva link after 3 tries. Check your DM for details.")
    logger.error(f"Error in /post after {max_tries} tries: {error_msg}")
    await context.bot.send_message(chat_id=BOT_ADMIN_ID, text=f"Error in /post after {max_tries} tries: {error_msg}")
    log_important(f"ERROR in /post after {max_tries} tries: {error_msg}")

async def lastlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    if not (user and user.id == BOT_ADMIN_ID):
        if message and hasattr(message, 'reply_text'):
            return await message.reply_text("🚫 Unauthorized.")
        return
    msg = last_posted_link or "No link posted yet."
    if message and hasattr(message, 'reply_text'):
        await message.reply_text(f"🔗 Last posted: {msg}")
    if message and hasattr(message, 'date'):
        log_important(f"/lastlink at {message.date}")

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    if not (user and user.id == BOT_ADMIN_ID):
        if message and hasattr(message, 'reply_text'):
            return await message.reply_text("🚫 Unauthorized.")
        return
    try:
        lines = open(IMPORTANT_LOG_PATH).read().splitlines()[-20:]
        text = "\n".join(lines)
        await context.bot.send_message(chat_id=BOT_ADMIN_ID, text=f"<code>{text}</code>", parse_mode="HTML")
        if message and hasattr(message, 'reply_text'):
            await message.reply_text("📬 Sent you the logs.")
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        await context.bot.send_message(chat_id=BOT_ADMIN_ID, text=f"Error reading logs: {e}")
        if message and hasattr(message, 'reply_text'):
            await message.reply_text("⚠️ Could not fetch logs.")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    if user and user.id == BOT_ADMIN_ID:
        if message and hasattr(message, 'reply_text'):
            await message.reply_text("💚 I’m alive and kicking!")
        if message and hasattr(message, 'date'):
            log_important(f"/health at {message.date}")
    else:
        if message and hasattr(message, 'reply_text'):
            await message.reply_text("🚫 Unauthorized.")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    if not (user and user.id == BOT_ADMIN_ID):
        if message and hasattr(message, 'reply_text'):
            return await message.reply_text("🚫 Unauthorized.")
        return
    if message and hasattr(message, 'reply_text'):
        await message.reply_text("🔄 Restarting…")
    await context.bot.send_message(chat_id=BOT_ADMIN_ID, text="🔄 Restart now.")
    if message and hasattr(message, 'date'):
        log_important(f"/restart at {message.date}")
    os._exit(1)

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

# --- Proxy Pool Management ---
import time
from collections import defaultdict

class ProxyPool:
    def __init__(self):
        self.stats = defaultdict(lambda: {'success': 0, 'fail': 0, 'last_fail': 0.0})
        self.cooldown = 600  # seconds to avoid a failed proxy
        self.bad_proxies = set()
        self.last_refresh = 0.0
        self.proxies = []

    async def refresh(self, fetch_func):
        # Only refresh every 10 minutes
        now = time.time()
        if now - self.last_refresh < 600 and self.proxies:
            return
        self.proxies = await fetch_func()
        self.last_refresh = now

    def get_proxy(self):
        # Return best proxy not in cooldown
        now = time.time()
        candidates = [p for p in self.proxies if now - self.stats[p]['last_fail'] > self.cooldown]
        if not candidates:
            return None
        # Sort by (fail, -success)
        candidates.sort(key=lambda p: (self.stats[p]['fail'], -self.stats[p]['success']))
        return candidates[0]

    def report(self, proxy, success):
        if not proxy:
            return
        if success:
            self.stats[proxy]['success'] += 1
        else:
            self.stats[proxy]['fail'] += 1
            self.stats[proxy]['last_fail'] = float(time.time())

proxy_pool = ProxyPool()

async def get_latest_canva_link_with_proxy_pool(retries=3, use_proxy=True):
    from scrape_links import fetch_free_proxies, get_stealth_headers
    import bs4
    main_url = "https://bingotingo.com/best-social-media-platforms/"
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(limit=5, ssl=ctx)
    await proxy_pool.refresh(fetch_free_proxies)
    for attempt in range(retries):
        proxy = proxy_pool.get_proxy() if use_proxy else None
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                headers = get_stealth_headers()
                resp1 = await session.get(main_url, headers=headers, proxy=proxy)
                resp1.raise_for_status()
                soup1 = BeautifulSoup(await resp1.text(), 'html.parser')
                download_btn = soup1.select_one('a.su-button')
                if not download_btn:
                    raise Exception("Download button not found on main page")
                latest_link = download_btn.get('href') if hasattr(download_btn, 'get') else None
                if not isinstance(latest_link, str):
                    raise Exception("Download button href is not a string")
                await asyncio.sleep(random.uniform(1.0, 2.5))
                headers = get_stealth_headers()
                resp2 = await session.get(latest_link, headers=headers, proxy=proxy)
                resp2.raise_for_status()
                soup2 = BeautifulSoup(await resp2.text(), 'html.parser')
                canva_link = None
                for a in soup2.find_all('a'):
                    if isinstance(a, bs4.element.Tag):
                        if 'href' in a.attrs:
                            href = a.attrs['href']
                            if isinstance(href, str) and href.startswith('https://www.canva.com/brand/'):
                                canva_link = href
                                break
                if not canva_link:
                    raise Exception("Canva link not found on redirected page")
                proxy_pool.report(proxy, True)
                return canva_link
        except Exception as e:
            proxy_pool.report(proxy, False)
            if attempt == retries - 1:
                raise
            await asyncio.sleep(random.uniform(2, 5))
    raise Exception("All proxies failed or no link found.")

def main():
    # Build & register handlers
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    for cmd, fn in [("start", start), ("help", help_command),
                    ("post", post), ("lastlink", lastlink),
                    ("logs", logs), ("health", health),
                    ("restart", restart)]:
        app.add_handler(CommandHandler(cmd, fn))
    app.add_handler(CallbackQueryHandler(vote_callback, pattern=r"^vote_"))
    # Kick off background services on the running loop
    loop = asyncio.get_event_loop()
    loop.create_task(start_health_server())
    logger.info("Starting polling…")
    app.run_polling()

if __name__ == "__main__":
    if platform.system() == "Windows" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(getattr(asyncio, "WindowsSelectorEventLoopPolicy")())
    main()
