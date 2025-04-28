# Canva Pro Links Telegram Bot

This project scrapes Canva links from a specific webpage and posts updates to a Telegram channel using a bot.

## Features
- Scrapes the latest Canva link from the webpage.
- Posts the link to a Telegram channel whenever it gets updated.
- Runs periodically to check for updates.
- Admin commands for bot control and status updates.
- Notifies the admin of any errors via DM.

## How It Works
- The bot scrapes the "Download" button link from the main page and follows it to find the Canva link.
- It keeps track of the last posted link in memory to ensure it doesn't repost the same link.
- The bot does not read channel messages; it relies on its internal tracking.

## Admin Features
- `/start`: Initialize the bot (admin only).
- `/status`: Check the last time the bot checked for links and the latest link it found (admin only).
- Error notifications: The bot sends error messages to the admin via DM.

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the bot:
   - Update `config.py` with your bot token, channel ID, and admin ID.

4. Run the bot:
   ```bash
   python bot.py
   ```

## Deployment
This project can be deployed on platforms like Koyeb. Ensure the environment variables for the bot token, channel ID, and admin ID are set correctly.