import aiohttp
import asyncio
from bs4 import BeautifulSoup
import random
import ssl

# List of rotating user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

def get_stealth_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Accept-Encoding": "identity",  # No encoding
        "Connection": "keep-alive",
        "DNT": "1",  # Do Not Track
        "Upgrade-Insecure-Requests": "1",
        "TE": "Trailers",  # Some websites check for this
        "Cache-Control": "max-age=0",
        "Pragma": "no-cache",  # No cache headers
        "Origin": "https://www.google.com/"
    }


async def get_latest_canva_link():
    main_url = "https://bingotingo.com/best-social-media-platforms/"
    sslcontext = ssl.create_default_context()
    
    connector = aiohttp.TCPConnector(limit_per_host=2, ssl=sslcontext)

    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            # Step 1: Get main page
            headers = get_stealth_headers()
            async with session.get(main_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch the main page: {response.status}")
                
                soup = BeautifulSoup(await response.text(), 'html.parser')
                download_button = soup.find('a', class_='su-button')
                if not download_button:
                    raise Exception("Download button not found on the main page")

                latest_link = download_button['href']

                # Human-like delay
                await asyncio.sleep(random.uniform(1.2, 2.8))

            # Step 2: Get redirected page
            headers = get_stealth_headers()
            async with session.get(latest_link, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch the redirected page: {response.status}")

                soup = BeautifulSoup(await response.text(), 'html.parser')
                canva_button = soup.find('a', href=lambda href: href and href.startswith('https://www.canva.com/brand/'))
                if not canva_button:
                    raise Exception("Canva link not found on the redirected page")

                return canva_button['href']

        except Exception as e:
            print(f"[Error] {e}")
            # Retry with exponential backoff
            await asyncio.sleep(random.uniform(2, 5))
            return await get_latest_canva_link()

if __name__ == "__main__":
    try:
        canva_link = asyncio.run(get_latest_canva_link())
        if canva_link:
            print(f"✅ Canva Link: {canva_link}")
        else:
            print("❌ No link found.")
    except Exception as e:
        print(f"🔥 Fatal Error: {e}")
