#!/usr/bin/env python3
import logging
import sys
import platform
import random
import os
import asyncio
from datetime import datetime, timedelta

import pytz
from aiohttp import web
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

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
            "• Scraping uses a smart proxy pool to avoid bans and maximize reliability."
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

# --- Message Formatting ---
def format_canva_post_message(latest_link, for_manual=True):
    msg = (
        f"✅ <b>New Canva Link:</b>\n{latest_link}\n\n"
        "🔔 Unmute to access first! ⏩\n"
        "⚡ <i>Powered by @CanvaProInviteLinks</i>\n"
        "<b>Backup:</b> <a href='https://t.me/+ejp2_sjBtJczY2I9'>Join our backup channel</a> in case of bans.\n"
        "<b>Proof:</b> After joining, send a screenshot to <a href='https://t.me/aenzBot'>@aenzBot</a>.\n"
    )
    if for_manual:
        msg += f"🎯 <b>Goal:</b> <i>Let's hit {random.randint(6, 12)} reactions! 🚀</i>\n\n"
    else:
        msg += f"💬 <b>Give <u>{random.randint(5,10)}</u> reactions for a fresh Canva invite link! The more reactions, the faster the next link drops! 🚀</b>"
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📣 Share Channel", url="https://t.me/share/url?url=https://t.me/CanvaProInviteLinks&text=🚀 Unlock daily Canva Pro team links! 🔥 Totally free, always fresh."),
            InlineKeyboardButton("🔗 Backup Channel", url="https://t.me/+ejp2_sjBtJczY2I9")
        ],
        [
            InlineKeyboardButton("🖼️ Send Proof", url="https://t.me/aenzBot")
        ]
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

    # Kick off background services on the running loop
    loop = asyncio.get_event_loop()
    loop.create_task(start_health_server())
    logger.info("Starting polling…")
    app.run_polling()

if __name__ == "__main__":
    if platform.system() == "Windows" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(getattr(asyncio, "WindowsSelectorEventLoopPolicy")())
    main()
