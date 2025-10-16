import re
from pathlib import Path
from typing import Dict
import asyncio
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("/tmp/scraper_results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def _safe_filename(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\-_. ]+", "_", s)
    return s[:100]

def call_black_box(payload: Dict) -> str:
    """
    Función sincrónica 'caja negra' que hace scraping con Playwright
    y guarda un resultado en disco.
    payload expected keys: { "path": "some/page", "extra": ... }
    """
    url_path = payload.get("path") or payload.get("url")
    if not url_path:
        raise ValueError("payload must include 'path' or 'url'")

    # Si el payload trae URL absoluta, la usamos; si trae path, la combinamos:
    if url_path.startswith("http://") or url_path.startswith("https://"):
        url = url_path
    else:
        base = payload.get("base") or "https://example.com"
        url = f"{base.rstrip('/')}/{url_path.lstrip('/')}"

    # Función interna async para Playwright
    async def _scrape(url: str) -> Dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)  # 30s timeout

            # Ejemplo: extraer title
            title = await page.title()

            # Ejemplo: extraer todos los h1
            h1_elements = await page.query_selector_all("h1")
            h1s = [await h.inner_text() for h in h1_elements]

            await browser.close()
            return {"title": title, "h1s": h1s}

    # Ejecutamos la función async de manera sincrónica
    result = asyncio.run(_scrape(url))

    # Guardar resultado en disco
    safe_name = _safe_filename(result["title"])
    out_path = OUTPUT_DIR / f"{safe_name}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write(f"TITLE: {result['title']}\n\n")
        f.write("H1s:\n")
        for h in result["h1s"]:
            f.write(f"- {h}\n")

    return str(out_path)
