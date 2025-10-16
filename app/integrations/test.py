import asyncio
import os
import shutil
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError
import uuid


BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
WORKS_DIR = BASE_DIR / "works"
DEBUG_DIR = BASE_DIR / "debug"

# Crear carpetas base
CACHE_DIR.mkdir(parents=True, exist_ok=True)
WORKS_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


async def scrape_signal(ids, work_id: str):
    """
    Descarga (o reutiliza) los CSVs de Mutational Signatures.

    - work_id: UUID o string del Work
    - ids: lista de Donor IDs (ej: ["DO46416", "DO36062"])
    """
    # Crear carpeta del Work
    work_dir = WORKS_DIR / work_id
    downloads_dir = work_dir / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    # Inicializar navegador
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        await page.goto("https://signal.mutationalsignatures.com/", timeout=60000)
        await page.wait_for_load_state("networkidle")

        for id_ in ids:
            safe_id = id_.replace("/", "_").replace("\\", "_")
            cached_csv = CACHE_DIR / f"{safe_id}.csv"
            work_csv = downloads_dir / f"{safe_id}.csv"

            # --- Si ya está en cache, crear symlink o copiar ---
            if cached_csv.exists():
                print(f"Usando cache existente para {id_}")
                try:
                    os.symlink(cached_csv.resolve(), work_csv)
                except OSError:
                    shutil.copy2(cached_csv, work_csv)
                continue

            # --- Si no está en cache, scrapear ---
            print(f"⚙️  Descargando CSV para {id_} ...")

            try:
                # Abrir input
                await page.click("div.Search__Container-sc-9sy7fy-1.jJwwcd")

                input_selector = "input[class*='text__Input'], input[class*='Text__Input'], input.bdWgKS"
                await page.wait_for_selector(
                    input_selector, timeout=15000, state="visible"
                )

                input_loc = page.locator(input_selector)
                await input_loc.click()
                await input_loc.fill(id_)

                # Esperar botón “Go to page”
                go_button_selector = "a[href^='/explore/cancerSample/'] div.PreviewPane__Button-sc-1qbxaw4-5"
                await page.wait_for_selector(
                    go_button_selector, timeout=15000, state="visible"
                )

                await page.click(go_button_selector)
                await page.wait_for_load_state("networkidle")

                # Esperar “Download as CSV”
                csv_button_selector = "button[label='Download as CSV']"
                await page.wait_for_selector(
                    csv_button_selector, timeout=20000, state="visible"
                )

                # Descargar
                async with page.expect_download() as download_info:
                    await page.click(csv_button_selector)
                download = await download_info.value

                # Guardar tanto en cache como en el Work
                await download.save_as(str(cached_csv))
                try:
                    os.symlink(cached_csv.resolve(), work_csv)
                except OSError:
                    shutil.copy2(cached_csv, work_csv)

                print(f"📥 CSV guardado y cacheado: {cached_csv}")

            except PWTimeoutError:
                # Guardar debug si falla
                debug_png = DEBUG_DIR / f"debug_{safe_id}.png"
                debug_html = DEBUG_DIR / f"debug_{safe_id}.html"

                await page.screenshot(path=str(debug_png), full_page=True)
                html = await page.content()
                debug_html.write_text(html, encoding="utf-8")

                print(f"⚠️ Timeout en {id_}. Debug: {debug_png}")
                continue

        await browser.close()

    print(f"Work completado: {work_dir}")
    return work_dir


# Ejemplo de uso
if __name__ == "__main__":
    test_work_id = str(uuid.uuid4())
    ids = ["DO46416", "DO36062"]
    asyncio.run(scrape_signal(ids, work_id=test_work_id))
