import aiohttp
import asyncio
from bs4 import BeautifulSoup
import random

# List of User-Agent strings to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
]

async def get_latest_canva_link():
    # Step 1: Scrape the "Download" button link from the main page
    main_url = "https://bingotingo.com/best-social-media-platforms/"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(main_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch the main page: {response.status}")

                soup = BeautifulSoup(await response.text(), 'html.parser')
                download_button = soup.find('a', class_='su-button')
                if not download_button:
                    raise Exception("Download button not found on the main page")

                latest_link = download_button['href']

                # Introduce a random delay
                await asyncio.sleep(random.uniform(1, 3))

                # Step 2: Visit the extracted link and scrape the Canva link
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                async with session.get(latest_link, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to fetch the redirected page: {response.status}")

                    soup = BeautifulSoup(await response.text(), 'html.parser')
                    # Update to find the Canva link based on its URL pattern
                    canva_button = soup.find('a', href=lambda href: href and href.startswith('https://www.canva.com/brand/'))
                    if not canva_button:
                        raise Exception("Canva link not found on the redirected page")

                    canva_link = canva_button['href']
                    return canva_link
        except Exception as e:
            print(f"Error: {e}")
            # Retry with exponential backoff
            await asyncio.sleep(random.uniform(2, 5))
            return await get_latest_canva_link()

if __name__ == "__main__":
    try:
        canva_link = asyncio.run(get_latest_canva_link())
        if canva_link:
            print(canva_link)
    except Exception as e:
        print(f"Error: {e}")
