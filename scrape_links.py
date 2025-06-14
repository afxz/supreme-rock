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

logger = logging.getLogger("scrape_links")

MAIN_URL = "https://bingotingo.com/best-social-media-platforms/"
BROWSERLESS_TOKEN = os.getenv("BROWSERLESS_TOKEN")
SCRAPEDO_TOKEN = os.getenv("SCRAPEDO_TOKEN")

# --- Browserless (BrowserQL) provider ---
def get_canva_link_browserless():
    if not BROWSERLESS_TOKEN:
        logger.error("[Browserless] API token not set in environment variable BROWSERLESS_TOKEN.")
        return None
    url = f"https://production-sfo.browserless.io/graphql?token={BROWSERLESS_TOKEN}"
    try:
        # Step 1: Fetch main page
        query1 = f'''
        mutation {{
          goto(url: \"{MAIN_URL}\", waitUntil: firstContentfulPaint) {{ status }}
          html {{ html }}
        }}
        '''
        resp1 = requests.post(url, json={"query": query1}, timeout=30)
        data1 = resp1.json()
        html1 = data1["data"]["html"]["html"]
        soup1 = BeautifulSoup(html1, "html.parser")
        btn = soup1.select_one("a.su-button")
        if not btn or not btn.get("href"):
            logger.warning("[Browserless] No redirect button found.")
            return None
        redirect_url = btn["href"]
        # Step 2: Fetch redirect page
        query2 = f'''
        mutation {{
          goto(url: \"{redirect_url}\", waitUntil: firstContentfulPaint) {{ status }}
          html {{ html }}
        }}
        '''
        resp2 = requests.post(url, json={"query": query2}, timeout=30)
        data2 = resp2.json()
        html2 = data2["data"]["html"]["html"]
        soup2 = BeautifulSoup(html2, "html.parser")
        for a in soup2.find_all('a'):
            if isinstance(a, bs4.element.Tag):
                href = a.get('href')
                if isinstance(href, str) and href.startswith('https://www.canva.com/brand/'):
                    logger.info("[Browserless] Found Canva link.")
                    return href
        logger.warning("[Browserless] No Canva link found on redirect page.")
        return None
    except Exception as e:
        logger.error(f"[Browserless] Exception: {e}")
        return None

# --- Scrape.do provider ---
def get_canva_link_scrapedo():
    if not SCRAPEDO_TOKEN:
        logger.error("[Scrape.do] API token not set in environment variable SCRAPEDO_TOKEN.")
        return None
    api_url = "http://api.scrape.do"
    try:
        params = {
            "token": SCRAPEDO_TOKEN,
            "url": MAIN_URL
        }
        resp1 = requests.get(api_url, params=params, timeout=30)
        html1 = resp1.text
        soup1 = BeautifulSoup(html1, "html.parser")
        btn = soup1.select_one("a.su-button")
        if not btn or not btn.get("href"):
            logger.warning("[Scrape.do] No redirect button found.")
            return None
        redirect_url = btn["href"]
        # Step 2: Fetch redirect page
        params2 = {
            "token": SCRAPEDO_TOKEN,
            "url": redirect_url
        }
        resp2 = requests.get(api_url, params=params2, timeout=30)
        html2 = resp2.text
        soup2 = BeautifulSoup(html2, "html.parser")
        for a in soup2.find_all('a'):
            if isinstance(a, bs4.element.Tag):
                href = a.get('href')
                if isinstance(href, str) and href.startswith('https://www.canva.com/brand/'):
                    logger.info("[Scrape.do] Found Canva link.")
                    return href
        logger.warning("[Scrape.do] No Canva link found on redirect page.")
        return None
    except Exception as e:
        logger.error(f"[Scrape.do] Exception: {e}")
        return None

# --- Try both providers before retrying ---
def get_latest_canva_link_via_api():
    providers = [get_canva_link_browserless, get_canva_link_scrapedo]
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
        link = await asyncio.to_thread(get_latest_canva_link_via_api)
        if link:
            return link
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
