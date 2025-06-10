import aiohttp
import asyncio
import random
import ssl
from bs4 import BeautifulSoup
import bs4

# List of rotating user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

# Fetch a list of free HTTPS proxies
async def fetch_free_proxies():
    url = "https://free-proxy-list.net/"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.text()
    soup = BeautifulSoup(text, 'html.parser')
    rows = soup.select("#proxylisttable tbody tr")
    proxies = []
    for row in rows:
        cols = row.find_all('td')
        ip, port, https = cols[0].text.strip(), cols[1].text.strip(), cols[6].text.strip()
        if https.lower() == 'yes':
            proxies.append(f"http://{ip}:{port}")
    return proxies

# Build stealth headers
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

# Main scraper function
async def get_latest_canva_link(retries=3, use_proxy=True):
    main_url = "https://bingotingo.com/best-social-media-platforms/"
    # Disable SSL verify (Codespaces friendly)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(limit=5, ssl=ctx)

    # Prepare proxies and headers
    proxies = await fetch_free_proxies() if use_proxy else []
    proxy = random.choice(proxies) if proxies else None

    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            # Step 1: fetch main page
            headers = get_stealth_headers()
            resp1 = await session.get(main_url, headers=headers, proxy=proxy if use_proxy and proxy else None)
            resp1.raise_for_status()
            soup1 = BeautifulSoup(await resp1.text(), 'html.parser')
            download_btn = soup1.select_one('a.su-button')
            if not download_btn:
                raise Exception("Download button not found on main page")
            latest_link = download_btn.get('href') if hasattr(download_btn, 'get') else None
            if not isinstance(latest_link, str):
                raise Exception("Download button href is not a string")
            await asyncio.sleep(random.uniform(1.0, 2.5))

            # Step 2: fetch redirect page
            headers = get_stealth_headers()
            resp2 = await session.get(latest_link, headers=headers, proxy=proxy if use_proxy and proxy else None)
            resp2.raise_for_status()
            soup2 = BeautifulSoup(await resp2.text(), 'html.parser')
            # Find the first <a> tag with an href that starts with the Canva brand link
            canva_link = None
            for a in soup2.find_all('a'):
                if isinstance(a, bs4.element.Tag):
                    href = a.attrs.get('href', None)
                    if isinstance(href, str) and href.startswith('https://www.canva.com/brand/'):
                        canva_link = href
                        break
            if not canva_link:
                raise Exception("Canva link not found on redirected page")
            return canva_link

        except Exception as e:
            if retries > 0:
                wait = random.uniform(2, 5)
                await asyncio.sleep(wait)
                return await get_latest_canva_link(retries - 1, use_proxy=use_proxy)
            else:
                raise

# Main scraper function with ProxyPool
async def get_latest_canva_link_with_proxy_pool(proxy_pool, retries=3, use_proxy=True):
    main_url = "https://bingotingo.com/best-social-media-platforms/"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(limit=5, ssl=ctx)
    await proxy_pool.refresh(fetch_free_proxies)
    for attempt in range(retries):
        proxy = proxy_pool.get_proxy() if use_proxy else None
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                headers = get_stealth_headers()
                resp1 = await session.get(main_url, headers=headers, proxy=proxy)
                resp1.raise_for_status()
                soup1 = BeautifulSoup(await resp1.text(), 'html.parser')
                download_btn = soup1.select_one('a.su-button')
                if not download_btn:
                    raise Exception("Download button not found on main page")
                # Fix: download_btn['href'] is a Tag, ensure it's a string
                latest_link = str(download_btn.get('href', ''))
                await asyncio.sleep(random.uniform(1.0, 2.5))
                headers = get_stealth_headers()
                resp2 = await session.get(latest_link, headers=headers, proxy=proxy)
                resp2.raise_for_status()
                soup2 = BeautifulSoup(await resp2.text(), 'html.parser')
                # Fix: robustly extract href attribute as string from Tag using dict access
                canva_link = None
                for a in soup2.find_all('a'):
                    href = None
                    # Only process if a is a Tag (not NavigableString/PageElement)
                    if type(a).__name__ == 'Tag':
                        try:
                            href = a['href']
                        except Exception:
                            continue
                    if isinstance(href, str) and href.startswith('https://www.canva.com/brand/'):
                        canva_link = href
                        break
                if not canva_link:
                    raise Exception("Canva link not found on redirected page")
                proxy_pool.report(proxy, True)
                return canva_link
        except Exception as e:
            proxy_pool.report(proxy, False)
            if attempt == retries - 1:
                raise
            await asyncio.sleep(random.uniform(2, 5))
    raise Exception("All proxies failed or no link found.")

# Entry point
if __name__ == "__main__":
    try:
        link = asyncio.run(get_latest_canva_link())
        print(f"✅ Canva Link: {link}")
    except Exception as e:
        print(f"🔥 Fatal Error: {e}")
