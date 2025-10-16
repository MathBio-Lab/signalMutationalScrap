import asyncio
import csv
import os
import shutil
import uuid
import random
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError
from app.utils.destructure_file import destructure_csvs


BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
WORKS_DIR = BASE_DIR / "works"
DEBUG_DIR = BASE_DIR / "debug"

# Crear carpetas base
CACHE_DIR.mkdir(parents=True, exist_ok=True)
WORKS_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

from pathlib import Path


def load_mapping_from_filename(upload_path: Path) -> dict[str, str]:
    """
    Lee un CSV con columnas SP y DO y devuelve un diccionario DO -> SP.
    upload_path: ruta completa al CSV de entrada
    """
    mapping = {}
    upload_path = Path(upload_path)
    with upload_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            donor_id = row["_PATIENT"].strip()
            sp_id = row["Donor_ID"].strip()
            mapping[donor_id] = sp_id
    return mapping


async def scrape_signal(ids, work_id: str):
    """
    Descarga (o reutiliza) los CSVs de Mutational Signatures.

    - work_id: UUID o string del Work
    - ids: lista de Donor IDs (ej: ["DO46416", "DO36062"])
    """
    work_dir = WORKS_DIR / work_id
    downloads_dir = work_dir / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

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
                # Sleep corto para no golpear el server innecesariamente
                await asyncio.sleep(0.1)
                continue

            # --- Si no está en cache, scrapear ---
            print(f"⚙️  Descargando CSV para {id_} ...")

            try:
                await page.click("div.Search__Container-sc-9sy7fy-1.jJwwcd")
                input_selector = "input[class*='text__Input'], input[class*='Text__Input'], input.bdWgKS"
                await page.wait_for_selector(
                    input_selector, timeout=15000, state="visible"
                )
                input_loc = page.locator(input_selector)
                await input_loc.click()
                await input_loc.fill(id_)

                go_button_selector = "a[href^='/explore/cancerSample/'] div.PreviewPane__Button-sc-1qbxaw4-5"
                await page.wait_for_selector(
                    go_button_selector, timeout=15000, state="visible"
                )
                await page.click(go_button_selector)
                await page.wait_for_load_state("networkidle")

                csv_button_selector = "button[label='Download as CSV']"
                await page.wait_for_selector(
                    csv_button_selector, timeout=20000, state="visible"
                )

                async with page.expect_download() as download_info:
                    await page.click(csv_button_selector)
                download = await download_info.value

                await download.save_as(str(cached_csv))
                try:
                    os.symlink(cached_csv.resolve(), work_csv)
                except OSError:
                    shutil.copy2(cached_csv, work_csv)

                print(f"📥 CSV guardado y cacheado: {cached_csv}")

                # --- Rate limit humano: sleep aleatorio 1-3s ---
                await asyncio.sleep(random.uniform(1, 3))

            except PWTimeoutError:
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


if __name__ == "__main__":
    test_work_id = str(uuid.uuid4())

    filename = "pcawg_ids_matched_DonorID_20251008_183516.csv"
    upload_path = Path(__file__).resolve().parents[1] / "uploads" / filename

    mapping = load_mapping_from_filename(upload_path)
    ids = list(mapping.keys())  # los DOs a scrapear

    # Ejecutar scraper
    work_dir = asyncio.run(scrape_signal(ids, work_id=test_work_id))

    # Procesar los CSV descargados
    destructure_csvs(work_dir, mapping)
