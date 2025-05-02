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
    if update.effective_user.id == BOT_ADMIN_ID:
        logger.info("/start command received.")
        log_important(f"/start by admin at {update.message.date}")
        await update.message.reply_text("🎉 Bot started! Use /help to see commands.")
    else:
        await update.message.reply_text("🚫 You’re not authorized.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BOT_ADMIN_ID:
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
        await update.message.reply_text(txt, parse_mode="HTML")
    else:
        await update.message.reply_text("🚫 Unauthorized.")

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_posted_link
    if update.effective_user.id != BOT_ADMIN_ID:
        return await update.message.reply_text("🚫 Unauthorized.")
    try:
        log_important(f"/post at {update.message.date}")
        await asyncio.sleep(random.uniform(1, 2.5))
        latest = await get_latest_canva_link(use_proxy=False)
        if latest and latest != last_posted_link:
            msg = (
                f"✅ <b>New Canva Link:</b>\n{latest}\n\n"
                "🔔 Unmute to access first! ⏩\n"
                "⚡ <i>Powered by @CanvaProInviteLinks</i>"
            )
            await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="HTML")
            last_posted_link = latest
            await update.message.reply_text("✅ Link posted.")
            log_important(f"Posted link: {latest}")
        elif latest == last_posted_link:
            await update.message.reply_text("ℹ️ No new link.")
            log_important("No new link found.")
        else:
            await update.message.reply_text("⚠️ Fetch failed.")
            log_important("Fetch returned no valid link.")
    except Exception as e:
        logger.error(f"Error in /post: {e}")
        await bot.send_message(chat_id=BOT_ADMIN_ID, text=f"Error in /post: {e}")
        await update.message.reply_text("❌ Something went wrong; check your DM.")
        log_important(f"ERROR in /post: {e}")

async def lastlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_ADMIN_ID:
        return await update.message.reply_text("🚫 Unauthorized.")
    msg = last_posted_link or "No link posted yet."
    await update.message.reply_text(f"🔗 Last posted: {msg}")
    log_important(f"/lastlink at {update.message.date}")

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_ADMIN_ID:
        return await update.message.reply_text("🚫 Unauthorized.")
    try:
        lines = open(IMPORTANT_LOG_PATH).read().splitlines()[-20:]
        text = "\n".join(lines)
        await bot.send_message(chat_id=BOT_ADMIN_ID, text=f"<code>{text}</code>", parse_mode="HTML")
        await update.message.reply_text("📬 Sent you the logs.")
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        await bot.send_message(chat_id=BOT_ADMIN_ID, text=f"Error reading logs: {e}")
        await update.message.reply_text("⚠️ Could not fetch logs.")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BOT_ADMIN_ID:
        await update.message.reply_text("💚 I’m alive and kicking!")
        log_important(f"/health at {update.message.date}")
    else:
        await update.message.reply_text("🚫 Unauthorized.")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_ADMIN_ID:
        return await update.message.reply_text("🚫 Unauthorized.")
    await update.message.reply_text("🔄 Restarting…")
    await bot.send_message(chat_id=BOT_ADMIN_ID, text="🔄 Restart now.")
    log_important(f"/restart at {update.message.date}")
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
    try:
        latest = await get_latest_canva_link(use_proxy=False)
        if latest and latest != last_posted_link:
            msg = (
                f"✅ <b>New Canva Link:</b>\n{latest}\n\n"
                "🔔 Unmute to access first! ⏩\n"
                "⚡ <i>Powered by @CanvaProInviteLinks</i>"
            )
            await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="HTML")
            last_posted_link = latest
            logger.info(f"Background posted: {latest}")
        else:
            logger.info("Background: no new link")
    except Exception as e:
        logger.error(f"Background error: {e}")
        await bot.send_message(chat_id=BOT_ADMIN_ID, text=f"BG error: {e}")

async def run_scheduler():
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

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
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
