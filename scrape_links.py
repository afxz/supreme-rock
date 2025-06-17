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
from config import SCRAPEDO_TOKENS  # <-- import tokens from config

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

# Scraping mode: 'scrapedo', 'direct', or 'both'
scraping_mode = 'direct'  # default

def set_scraping_mode(mode):
    global scraping_mode
    if mode in ('scrapedo', 'direct', 'both'):
        scraping_mode = mode
        logger.info(f"[Scraper] Scraping mode set to: {mode}")
        return True
    return False

def get_scraping_mode():
    return scraping_mode

def get_canva_link_scrapedo_main():
    if not SCRAPEDO_TOKENS:
        logger.error("[Scrape.do] No API tokens set in environment variable SCRAPEDO_TOKENS.")
        return None
    api_url = "http://api.scrape.do"
    tokens = SCRAPEDO_TOKENS[:]
    random.shuffle(tokens)
    for token in tokens:
        try:
            params = {
                "token": token,
                "url": MAIN_URL
            }
            resp = requests.get(api_url, params=params, timeout=30)
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            btn = soup.select_one("a.su-button")
            if btn and btn.get("href"):
                return btn["href"]
        except Exception as e:
            logger.error(f"[Scrape.do] Exception with token {token}: {e}")
    return None

async def fetch_canva_link_from_redirect(redirect_url):
    if not SCRAPEDO_TOKENS:
        logger.error("[Scrape.do] No API tokens set in environment variable SCRAPEDO_TOKENS.")
        return None
    api_url = "http://api.scrape.do"
    tokens = SCRAPEDO_TOKENS[:]
    random.shuffle(tokens)
    for token in tokens:
        params = {
            "token": token,
            "url": redirect_url
        }
        try:
            def fetch_html():
                resp = requests.get(api_url, params=params, timeout=30)
                return resp.text
            html = await asyncio.to_thread(fetch_html)
            soup = BeautifulSoup(html, "html.parser")
            found = False
            for a in soup.find_all('a'):
                if isinstance(a, bs4.element.Tag):
                    href = a.get('href')
                    if isinstance(href, str) and href.startswith('https://www.canva.com/brand/'):
                        return href
            # Try to find any Canva link in the HTML, even if not in <a> tags
            import re
            canva_match = re.search(r'https://www.canva.com/brand/join\?token=[^"\'\s<>]+', html)
            if canva_match:
                return canva_match.group(0)
            logger.error(f"[Scrape.do] No Canva link found in redirect page. HTML snippet: {html[:500]}")
        except Exception as e:
            logger.error(f"[Scrape.do] Exception in fetch_canva_link_from_redirect with token {token}: {e}")
    return None

# --- Direct scraping fallback (non-Scrape.do) ---
def get_canva_link_direct_main():
    try:
        resp = requests.get(MAIN_URL, headers=get_stealth_headers(), timeout=30)
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        btn = soup.select_one("a.su-button")
        if btn and btn.get("href"):
            return btn["href"]
    except Exception as e:
        logger.error(f"[Direct] Exception: {e}")
    return None

async def fetch_canva_link_from_redirect_direct(redirect_url):
    try:
        def fetch_html():
            resp = requests.get(redirect_url, headers=get_stealth_headers(), timeout=30)
            return resp.text
        html = await asyncio.to_thread(fetch_html)
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all('a'):
            if isinstance(a, bs4.element.Tag):
                href = a.get('href')
                if isinstance(href, str) and href.startswith('https://www.canva.com/brand/'):
                    return href
        # Regex fallback
        import re
        canva_match = re.search(r'https://www.canva.com/brand/join\?token=[^"\'\s<>]+', html)
        if canva_match:
            return canva_match.group(0)
        logger.error(f"[Direct] No Canva link found in redirect page. HTML snippet: {html[:500]}")
    except Exception as e:
        logger.error(f"[Direct] Exception in fetch_canva_link_from_redirect: {e}")
    return None

# --- Main scraping logic (mode aware) ---
def get_latest_redirect_link_via_api():
    mode = get_scraping_mode()
    if mode in ('direct', 'both'):
        link = get_canva_link_direct_main()
        if link:
            logger.info("[Scraper] Success with direct scraping")
            return link
        elif mode == 'direct':
            logger.error("[Scraper] Direct scraping returned no link.")
            return None
    if mode in ('scrapedo', 'both'):
        link = get_canva_link_scrapedo_main()
        if link:
            logger.info("[Scraper] Success with Scrape.do")
            return link
        else:
            logger.error("[Scraper] Scrape.do returned no link.")
    return None

async def fetch_canva_link_from_redirect_mode(redirect_url):
    mode = get_scraping_mode()
    if mode in ('direct', 'both'):
        link = await fetch_canva_link_from_redirect_direct(redirect_url)
        if link:
            return link
    if mode in ('scrapedo', 'both'):
        link = await fetch_canva_link_from_redirect(redirect_url)
        if link:
            return link
    return None

# --- Async wrapper for bot usage ---
async def get_latest_canva_link():
    try:
        redirect_url = await asyncio.to_thread(get_latest_redirect_link_via_api)
        if redirect_url:
            canva_link = await fetch_canva_link_from_redirect_mode(redirect_url)
            if canva_link:
                return canva_link
            else:
                logger.warning(f"[Scraper] Redirect page did not yield Canva link.")
        return None
    except Exception as e:
        logger.error(f"[Scraper] Exception in get_latest_canva_link: {e}")
        return None

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
