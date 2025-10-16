import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("/tmp/scraper_results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def scrape_signal(ids):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=True para ejecución en background
        page = await browser.new_page()
        await page.goto("https://signal.mutationalsignatures.com/", timeout=60000)

        screenshots = []

        for id_ in ids:
            # Click en el div que abre el input
            await page.click('div.Search__Container-sc-9sy7fy-1.jJwwcd')

            # Esperar a que aparezca el input
            await page.wait_for_selector('input.Text__Input-sc-l28shj-1.bdWgKS', timeout=5000)

            # Escribir el ID en el input
            await page.fill('input.Text__Input-sc-l28shj-1.bdWgKS', id_)

            # Opción: presionar Enter si eso dispara la búsqueda
            await page.keyboard.press("Enter")

            # Esperar a que el resultado se renderice
            # Aquí podrías usar un selector del contenedor principal del resultado
            await page.wait_for_timeout(3000)  # espera 3 segundos para que React renderice (ajustable)

            # Guardar captura de pantalla
            safe_id = id_.replace("/", "_").replace("\\", "_")
            screenshot_path = OUTPUT_DIR / f"{safe_id}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            screenshots.append(str(screenshot_path))

        await browser.close()
        return screenshots

# Uso
ids = ["DO46416"]
res = asyncio.run(scrape_signal(ids))
for r in res:
    print("Screenshot saved at:", r)
