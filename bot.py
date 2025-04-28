import asyncio
from health_check import start_health_check_server, self_ping
from link_checker import check_links
from telegram_bot import create_bot_application, start, status
from telegram.ext import CommandHandler
from loguru import logger

# Configure loguru for structured logging
logger.add("bot.log", rotation="10 MB", retention="7 days", level="INFO")

async def main():
    # Start the health check server
    start_health_check_server()

    # Start the self-ping mechanism
    self_ping()

    # Initialize the bot application
    application = create_bot_application()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))

    # Run the bot and link checker concurrently
    await asyncio.gather(
        application.run_polling(),
        check_links()
    )

if __name__ == "__main__":
    asyncio.run(main())