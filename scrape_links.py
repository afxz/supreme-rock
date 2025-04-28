import requests
from bs4 import BeautifulSoup

def get_latest_canva_link():
    # Step 1: Scrape the "Download" button link from the main page
    main_url = "https://bingotingo.com/best-social-media-platforms/"
    response = requests.get(main_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch the main page: {response.status_code}")

    soup = BeautifulSoup(response.text, 'html.parser')
    download_button = soup.find('a', class_='su-button')
    if not download_button:
        raise Exception("Download button not found on the main page")

    latest_link = download_button['href']

    # Step 2: Visit the extracted link and scrape the Canva link
    response = requests.get(latest_link)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch the redirected page: {response.status_code}")

    soup = BeautifulSoup(response.text, 'html.parser')
    # Update to find the Canva link based on its URL pattern
    canva_button = soup.find('a', href=lambda href: href and href.startswith('https://www.canva.com/brand/'))
    if not canva_button:
        raise Exception("Canva link not found on the redirected page")

    canva_link = canva_button['href']
    return canva_link

if __name__ == "__main__":
    try:
        canva_link = get_latest_canva_link()
        print(f"Latest Canva link: {canva_link}")
    except Exception as e:
        print(f"Error: {e}")