#!/usr/bin/env python3
import logging
import sys
import platform
import random
import os
import asyncio
from datetime import datetime, timedelta

import pytz
import schedule
from aiohttp import web
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from scrape_links import get_latest_canva_link
from config import BOT_TOKEN, CHANNEL_ID, BOT_ADMIN_ID, IMPORTANT_LOG_PATH

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
            "<b>Auto-Posting Schedule (IST):</b>\n"
            "• 04:00–06:00 (4–6 AM)\n"
            "• 09:00–11:00 (9–11 AM)\n"
            "• 13:00–15:00 (1–3 PM)\n"
            "• 18:00–21:00 (6–9 PM)\n"
            "• 00:00–03:00 (12–3 AM)\n"
            "\nPosts are sent at random times within these slots each day."
        )
        if message and hasattr(message, 'reply_text'):
            await message.reply_text(txt, parse_mode="HTML")
    else:
        if message and hasattr(message, 'reply_text'):
            await message.reply_text("🚫 Unauthorized.")

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
                msg, keyboard = format_canva_post_message(latest, for_manual=True)
                sent_msg = await context.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="HTML", reply_markup=keyboard)
                last_posted_link = latest
                if message and hasattr(message, 'reply_text'):
                    await message.reply_text("✅ Link posted.")
                log_important(f"Posted link: {latest}")
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
    # If we reach here, all tries failed
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

# --- Scheduling ---
IST = pytz.timezone("Asia/Kolkata")

def random_time(start_h, end_h):
    base = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    start = base + timedelta(hours=start_h)
    end = base + timedelta(hours=end_h)
    return start + timedelta(seconds=random.randint(0, int((end-start).total_seconds())))

def schedule_posting():
    slots = [(4,6),(9,11),(13,15),(18,21),(0,3)]
    for s,e in slots:
        t = random_time(s,e).strftime("%H:%M")
        schedule.every().day.at(t).do(lambda: asyncio.create_task(post_latest_link()))
    logger.info("Posting slots scheduled")

async def post_latest_link():
    global last_posted_link
    try_count = 0
    max_tries = 3
    latest = None
    error_msg = None
    while try_count < max_tries:
        try:
            latest = await get_latest_canva_link(use_proxy=False)
            if latest and latest != last_posted_link:
                msg, keyboard = format_canva_post_message(latest, for_manual=False)
                await Bot.send_message(self=bot, chat_id=CHANNEL_ID, text=msg, parse_mode="HTML", reply_markup=keyboard)
                last_posted_link = latest
                logger.info(f"Background posted: {latest}")
                return
            elif latest == last_posted_link:
                logger.info("Background: no new link")
                return
            else:
                error_msg = "Fetch returned no valid link."
        except Exception as e:
            error_msg = str(e)
        try_count += 1
    logger.error(f"Background error after {max_tries} tries: {error_msg}")
    await Bot.send_message(self=bot, chat_id=BOT_ADMIN_ID, text=f"BG error after {max_tries} tries: {error_msg}")

async def run_scheduler():
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

# --- Message Formatting ---
def format_canva_post_message(latest_link, for_manual=True):
    msg = (
        f"✅ <b>New Canva Link:</b>\n{latest_link}\n\n"
        "🔔 Unmute to access first! ⏩\n"
        "⚡ <i>Powered by @CanvaProInviteLinks</i>\n"
    )
    if for_manual:
        msg += f"🎯 <b>Goal:</b> <i>Let's hit {random.randint(14, 22)} reactions! 🚀</i>\n\n"
    else:
        msg += f"💬 <b>Give <u>{random.randint(5,10)}</u> reactions to this message for a fresh Canva invite link!\nThe more reactions, the faster the next link drops! 🚀</b>"
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    share_url = (
        "https://t.me/share/url?url=https://t.me/CanvaProInviteLinks&text="
        "🚀 Unlock daily Canva Pro team links! 🔥 Totally free, always fresh. Join us now: https://t.me/CanvaProInviteLinks"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 Share this Channel", url=share_url)]
    ])
    return msg, keyboard

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

def main():
    # Build & register handlers
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    for cmd, fn in [("start", start), ("help", help_command),
                    ("post", post), ("lastlink", lastlink),
                    ("logs", logs), ("health", health),
                    ("restart", restart)]:
        app.add_handler(CommandHandler(cmd, fn))

    # Kick off background services on the running loop
    loop = asyncio.get_event_loop()
    loop.create_task(start_health_server())
    schedule_posting()
    loop.create_task(run_scheduler())

    logger.info("Starting polling…")
    app.run_polling()

if __name__ == "__main__":
    if platform.system() == "Windows" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(getattr(asyncio, "WindowsSelectorEventLoopPolicy")())
    main()
