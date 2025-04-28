# Canva Pro Links Telegram Bot

This project scrapes Canva links from a specific webpage and posts updates to a Telegram channel using a bot.

## Features
- Scrapes the latest Canva link from the webpage.
- Posts the link to a Telegram channel whenever it gets updated.
- Runs periodically to check for updates.

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
   - Update `config.py` with your bot token and channel ID.

4. Run the bot:
   ```bash
   python bot.py
   ```

## Deployment
This project can be deployed on platforms like Koyeb. Ensure the environment variables for the bot token and channel ID are set correctly.