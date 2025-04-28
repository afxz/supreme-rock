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
- If the latest link is the same as the last posted link, it will not post it again, preventing duplicate posts.

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

## Environment Variable Validation
The bot validates the following environment variables at startup to ensure they are correctly configured:
- `BOT_TOKEN`: The Telegram bot token.
- `CHANNEL_ID`: The Telegram channel ID.
- `ADMIN_GROUP_ID`: The admin group ID for bot control.

If any of these variables are missing or invalid, the bot will raise an error and exit.

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

## Common Issues and Fixes
- **Duplicate Links Posted**: This issue occurs if the bot fails to track the last posted link properly. The latest update ensures that the bot only posts new or updated links.
- **Error Notifications**: Any errors encountered during execution are sent to the admin group for quick resolution.

## Health Check
The bot includes a simple HTTP server running on port 8080 to support health checks. This ensures compatibility with deployment platforms that require health checks.