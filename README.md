# Canva Pro Links Telegram Bot

This project automates the process of scraping Canva Pro invite links from a specific website and posting them to a Telegram channel. It is designed for reliability, admin control, and easy deployment.

**Live Channel:**
👉 [t.me/CanvaProInviteLinks](https://telegram.me/CanvaProInviteLinks)

---

## Features

- **Manual and Automated Posting:**
  - Manual mode: Admin can trigger posting with a command (`/post`).
  - Automated mode: Bot checks for new links every 5 minutes and posts if a new link is found.

- **Admin Controls:**
  - `/start` – Start the bot (admin only)
  - `/help` – List admin commands
  - `/post` – Scrape and post the latest Canva link (manual mode)
  - `/lastlink` – Show the last posted link
  - `/logs` – Get the last 20 lines of important logs (in code style)
  - `/health` – Check if the bot is running
  - `/restart` – Restart the bot server

- **Error Handling:**
  - All errors and important events are logged to `important.log` and sent to the admin’s DM.
  - Log files are auto-truncated to prevent unlimited growth.

- **Health Check:**
  - HTTP server on port 8080 for deployment health checks.

---

## How It Works

- The bot scrapes the "Download" button from the target page and follows redirects to extract the latest Canva Pro invite link.
- It keeps track of the last posted link to avoid duplicates.
- Admin can manually trigger posting or check logs/status at any time.

---

## Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd canova-robot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Copy `sample.env` to `.env` and fill in your values:
     ```
     BOT_TOKEN=your-telegram-bot-token
     CHANNEL_ID=@your-channel-id
     ADMIN_GROUP_ID=-1001234567890
     BOT_ADMIN_ID=your-telegram-user-id
     ```

4. **Run the bot:**
   ```bash
   python bot_manual.py
   ```
   Or for automated mode:
   ```bash
   python bot.py
   ```

---

## Deployment on Koyeb

1. **Push your code to GitHub.**
2. **Create a new app on [Koyeb](https://www.koyeb.com/):**
   - Select your GitHub repo as the source.
   - Set the build command: `pip install -r requirements.txt`
   - Set the run command: `python bot_manual.py` (or `python bot.py`)
   - Add environment variables as in your `.env`.
   - Ensure port 8080 is used for health checks.
3. **Deploy and monitor logs via the Koyeb dashboard.**

---

## Notes

- The bot is designed to be robust and admin-friendly.
- Log files are automatically truncated to the last 1000 lines on each startup.
- All admin commands are restricted to the configured admin user.

---

**Live Channel:**
👉 [t.me/CanvaProInviteLinks](https://telegram.me/CanvaProInviteLinks)
