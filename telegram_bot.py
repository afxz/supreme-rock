import asyncio
import logging
import os
from aiohttp import web
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)
from config import BOT_TOKEN, CHANNEL_ID, ADMIN_GROUP_ID
from scrape_links import get_latest_canva_link

logging.basicConfig(level=logging.INFO)

last_posted_link = None
last_checked = None

async def post_new_link(app):
    global last_posted_link, last_checked
    while True:
        try:
            canva_link = await get_latest_canva_link()
            last_checked = datetime.utcnow()
            if canva_link != last_posted_link:
                await app.bot.send_message(chat_id=CHANNEL_ID, text=f"New Canva Link: {canva_link}")
                last_posted_link = canva_link
        except Exception as e:
            await app.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"Error: {e}")
        await asyncio.sleep(300)  # 5 minutes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == ADMIN_GROUP_ID:
        await update.message.reply_text("Bot started and running.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == ADMIN_GROUP_ID:
        msg = f"Last checked: {last_checked}\nLast posted link: {last_posted_link}"
        await update.message.reply_text(msg)

def run_health_check():
    async def handle(request):
        return web.Response(text="OK")
    app = web.Application()
    app.router.add_get("/", handle)
    return app

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    # Start periodic task
    asyncio.create_task(post_new_link(application))
    # Start health check server
    runner = web.AppRunner(run_health_check())
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    # Run the bot
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
