# strings.py

HELP_MSG = (
    "<b>Admin Commands:</b>\n"
    "/post - Scrape & post the latest link\n"
    "/now &lt;canva_link&gt; - Manually post a Canva link to the channel (with natural voting)\n"
    "/setinterval &lt;min_seconds&gt; &lt;max_seconds&gt; - Set auto-post interval (e.g. /setinterval 300 400)\n"
    "/help - This menu\n"
    "/lastlink - Show the last posted Canva link\n"
    "/logs - Show recent important logs\n"
    "/health - Check bot health\n"
    "/restart - Restart the bot (Koyeb will auto-restart)\n"
    "/setscrapemode &lt;code&gt;scrapedo&lt;/code&gt;|&lt;code&gt;direct&lt;/code&gt;|&lt;code&gt;both&lt;/code&gt; - Enable/disable scraping methods.\n"
    "/stats - Show bot stats and current settings.\n"
    "\n"
    "<b>Auto-Posting Info:</b>\n"
    "• The bot automatically checks for new Canva links at a random interval you set.\n"
    "• Use /setinterval to change the interval at any time.\n"
    "• A new link is posted to the channel as soon as it is detected.\n"
    "• Scraping is done via Scrape.do and/or direct, with multiple API keys supported.\n"
    "\n"
    "<b>Channel Post Format:</b>\n"
    "- Each post contains the Canva link, a proof/verification instruction, and two buttons: Share Channel and Join Backup.\n"
    "- Users can vote if the link is working or not using fun random emojis. Vote counts update live and may increase naturally.\n"
)

START_MSG = "🎉 Bot started! Use /help to see commands."
UNAUTHORIZED_MSG = "🚫 You’re not authorized."
USAGE_SETINTERVAL = "Usage: /setinterval <min_seconds> <max_seconds>\nExample: /setinterval 300 400"
INVALID_INTERVAL = "Invalid values. min >= 60, max >= min."
ERROR_GENERIC = "An error occurred. Please try again."
USAGE_SET_SCRAPE_MODE = "Usage: /setscrapemode <code>scrapedo</code>|<code>direct</code>|<code>both</code>\nExample: /setscrapemode <code>scrapedo</code>"

