import httpx
from bs4 import BeautifulSoup

class WebScraper:
    BASE_URL = "https://example.com"

    async def fetch_data(self, path: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}/{path}")
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find("title").text if soup.find("title") else "No title"
        return {"title": title}
