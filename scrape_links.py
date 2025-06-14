import aiohttp
import asyncio
import random
import ssl
from bs4 import BeautifulSoup
import bs4
import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

def get_stealth_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "Pragma": "no-cache"
    }

logger = logging.getLogger("scrape_links")

MAIN_URL = "https://bingotingo.com/best-social-media-platforms/"
BROWSERLESS_TOKEN = os.getenv("BROWSERLESS_TOKEN")
SCRAPEDO_TOKEN = os.getenv("SCRAPEDO_TOKEN")

async def fetch_canva_link_from_redirect(redirect_url):
    import aiohttp
    headers = get_stealth_headers()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(limit=5, ssl=ctx)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(redirect_url, headers=headers) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all('a'):
                if isinstance(a, bs4.element.Tag):
                    href = a.get('href')
                    if isinstance(href, str) and href.startswith('https://www.canva.com/brand/'):
                        return href
    return None

# --- Browserless (BrowserQL) provider ---
def get_canva_link_browserless_main():
    if not BROWSERLESS_TOKEN:
        logger.error("[Browserless] API token not set in environment variable BROWSERLESS_TOKEN.")
        return None
    endpoint = f"https://production-sfo.browserless.io/chromium/bql?token={BROWSERLESS_TOKEN}"
    try:
        query = '''
        mutation Scrape($url: String!) {
          reject(type: [image, media, font, stylesheet]) { enabled time }
          goto(url: $url, waitUntil: firstContentfulPaint) { status }
          waitFor(selector: \"a.su-button\", timeout: 65000) { selector }
          html { html }
        }
        '''
        variables = {"url": MAIN_URL}
        resp = requests.post(endpoint, json={"query": query, "variables": variables}, timeout=70)
        try:
            data = resp.json()
        except Exception as e:
            logger.error(f"[Browserless] JSON decode error: {e}. Raw response: {resp.text}")
            return None
        html = data.get("data", {}).get("html", {}).get("html", "")
        if not html:
            logger.warning("[Browserless] No HTML returned for main page.")
            return None
        soup = BeautifulSoup(html, "html.parser")
        btn = soup.select_one("a.su-button")
        if not btn or not btn.get("href"):
            logger.warning("[Browserless] No redirect button found. HTML snippet: %s", html[:500])
            try:
                with open("browserless_main.html", "w", encoding="utf-8") as f:
                    f.write(html)
                logger.info("[Browserless] Full HTML saved to browserless_main.html for inspection.")
            except Exception as e:
                logger.error(f"[Browserless] Failed to save HTML: {e}")
            return None
        redirect_url = btn["href"]
        return redirect_url
    except Exception as e:
        logger.error(f"[Browserless] Exception: {e}")
        return None

# --- Scrape.do provider ---
def get_canva_link_scrapedo_main():
    if not SCRAPEDO_TOKEN:
        logger.error("[Scrape.do] API token not set in environment variable SCRAPEDO_TOKEN.")
        return None
    api_url = "http://api.scrape.do"
    try:
        params = {
            "token": SCRAPEDO_TOKEN,
            "url": MAIN_URL
        }
        resp = requests.get(api_url, params=params, timeout=30)
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        btn = soup.select_one("a.su-button")
        if not btn or not btn.get("href"):
            logger.warning("[Scrape.do] No redirect button found.")
            return None
        redirect_url = btn["href"]
        return redirect_url
    except Exception as e:
        logger.error(f"[Scrape.do] Exception: {e}")
        return None

# --- Try both providers for MAIN_URL, then fetch redirect locally ---
def get_latest_redirect_link_via_api():
    providers = [get_canva_link_browserless_main, get_canva_link_scrapedo_main]
    random.shuffle(providers)
    errors = []
    for provider in providers:
        try:
            link = provider()
            if link:
                logger.info(f"[Scraper] Success with {provider.__name__}")
                return link
            else:
                errors.append(f"{provider.__name__} returned no link.")
        except Exception as e:
            logger.error(f"[Scraper] {provider.__name__} failed: {e}")
            errors.append(f"{provider.__name__} exception: {e}")
    logger.error(f"[Scraper] Both providers failed: {' | '.join(errors)}")
    return None

# --- Async wrapper for bot usage ---
async def get_latest_canva_link(retries=3):
    for attempt in range(retries):
        redirect_url = await asyncio.to_thread(get_latest_redirect_link_via_api)
        if redirect_url:
            canva_link = await fetch_canva_link_from_redirect(redirect_url)
            if canva_link:
                return canva_link
            else:
                logger.warning(f"[Scraper] Redirect page did not yield Canva link.")
        logger.warning(f"[Scraper] Attempt {attempt+1} failed, retrying...")
        await asyncio.sleep(random.uniform(2, 5))
    raise Exception("All providers failed to fetch Canva link after retries.")

# Entry point for manual testing
def main():
    logging.basicConfig(level=logging.INFO)
    try:
        link = asyncio.run(get_latest_canva_link())
        print(f"✅ Canva Link: {link}")
    except Exception as e:
        print(f"🔥 Fatal Error: {e}")

if __name__ == "__main__":
    main()
