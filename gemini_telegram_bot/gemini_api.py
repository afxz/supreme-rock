import aiohttp
import random
from config import GEMINI_API_KEYS

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

async def gemini_generate_content(prompt: str) -> str:
    api_key = random.choice([k for k in GEMINI_API_KEYS if k.strip()])
    url = GEMINI_API_URL.format(api_key=api_key)
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            resp.raise_for_status()
            result = await resp.json()
            # Extract the generated text
            try:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                return "[Gemini API Error: Unexpected response format]"
