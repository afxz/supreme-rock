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
- `/restart`: Restart the bot server (admin group only).
- `/logs`: Fetch the last 20 lines of logs (admin group only).
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

Make sure to replace the placeholders with your actual values.

## Deployment on Koyeb

This project is now deployable on Koyeb. Follow these steps to deploy:

1. **Create a Koyeb Account**
   - Go to [Koyeb](https://www.koyeb.com/) and create an account if you don't already have one.

2. **Create a New App**
   - Log in to your Koyeb dashboard.
   - Click on "Create App" and select "GitHub" as the source.
   - Connect your GitHub repository containing this project.

3. **Set Environment Variables**
   - In the "Environment Variables" section, add the following variables:
     - `BOT_TOKEN`: Your Telegram bot token.
     - `CHANNEL_ID`: Your Telegram channel ID.
     - `ADMIN_GROUP_ID`: Your admin group ID.
     - `BOT_ADMIN_ID`: Your bot admin ID.

4. **Set the Port**
   - Koyeb requires a health check endpoint. This project includes a health check server running on port `8080`. Ensure that Koyeb is configured to use this port.

5. **Deploy the App**
   - Click "Deploy" to start the deployment process.
   - Once deployed, your bot will be live and accessible.

6. **Monitor Logs**
   - Use the Koyeb dashboard to monitor logs and ensure the bot is running correctly.

### Health Check
- The bot includes a health check endpoint at `/health` on port `8080`. Koyeb will use this endpoint to verify that the bot is running.
