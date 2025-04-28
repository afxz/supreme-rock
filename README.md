# Canva Pro Links Telegram Bot

This project scrapes Canva links from a specific webpage and posts updates to a Telegram channel using a bot.

## Features
- Scrapes the latest Canva link from the webpage.
- Posts the link to a Telegram channel whenever it gets updated.
- Runs periodically to check for updates.
- Admin commands for bot control and status updates (restricted to the admin group).
- Notifies the admin group of any errors via messages.

## How It Works
- The bot scrapes the "Download" button link from the main page and follows it to find the Canva link.
- It keeps track of the last posted link in memory to ensure it doesn't repost the same link.
- The bot does not read channel messages; it relies on its internal tracking.

## Admin Features
- `/start`: Initialize the bot (admin group only).
- `/status`: Check the last time the bot checked for links and the latest link it found (admin group only).
- Error notifications: The bot sends error messages to the admin group.

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
   - Update `config.py` with your bot token, channel ID, and admin group ID.

4. Run the bot:
   ```bash
   python bot.py
   ```

## Environment Variables
This project uses a `.env` file to store sensitive information. Create a `.env` file in the root directory with the following variables:

```
BOT_TOKEN=your-bot-token-here
CHANNEL_ID=@your-channel-id-here
ADMIN_GROUP_ID=-1001234567890
```

Make sure to replace the placeholders with your actual values.

## Deployment
This project can be deployed on platforms like Koyeb. Ensure the environment variables for the bot token, channel ID, and admin group ID are set correctly.

### Docker Deployment
1. Build the Docker image:
   ```bash
   docker build -t canva-bot .
   ```

2. Run the Docker container:
   ```bash
   docker run -d --name canva-bot -e BOT_TOKEN=<your-bot-token> -e CHANNEL_ID=<your-channel-id> -e ADMIN_GROUP_ID=<your-admin-group-id> canva-bot
   ```