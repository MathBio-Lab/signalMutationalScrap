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

# Create base folders
CACHE_DIR.mkdir(parents=True, exist_ok=True)
WORKS_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def load_mapping_from_filename(upload_path: Path) -> dict[str, str]:
    """
    Reads a CSV file with columns SP and DO and returns a dictionary DO -> SP.
    upload_path: full path to the input CSV
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
    Downloads (or reuses) Mutational Signatures CSVs.

    - work_id: UUID or string identifier for the job
    - ids: list of Donor IDs (e.g. ["DO46416", "DO36062"])
    """
    work_dir = WORKS_DIR / work_id
    downloads_dir = work_dir / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        await page.goto("https://signal.mutationalsignatures.com/", timeout=60000)
        await page.wait_for_load_state("networkidle")

        downloaded_count = 0  # track only actual downloads

        for idx, id_ in enumerate(ids, start=1):
            safe_id = id_.replace("/", "_").replace("\\", "_")
            cached_csv = CACHE_DIR / f"{safe_id}.csv"
            work_csv = downloads_dir / f"{safe_id}.csv"

            # --- Use existing cache if available ---
            if cached_csv.exists():
                print(f"Using cached file for {id_}")
                try:
                    os.symlink(cached_csv.resolve(), work_csv)
                except OSError:
                    shutil.copy2(cached_csv, work_csv)
                await asyncio.sleep(0.1)
                continue

            # --- Download CSV if not cached ---
            print(f"⚙️  Downloading CSV for {id_} ...")

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

                print(f"📥 CSV saved and cached: {cached_csv}")

                downloaded_count += 1  # increment only when actually downloaded

                # --- Random sleep between downloads to avoid rate limiting ---
                await asyncio.sleep(random.uniform(1, 3))

            except PWTimeoutError:
                debug_png = DEBUG_DIR / f"debug_{safe_id}.png"
                debug_html = DEBUG_DIR / f"debug_{safe_id}.html"
                await page.screenshot(path=str(debug_png), full_page=True)
                html = await page.content()
                debug_html.write_text(html, encoding="utf-8")
                print(f"⚠️ Timeout on {id_}. Debug saved at: {debug_png}")
                continue

            # --- Restart browser and context every 60 IDs to avoid memory leaks ---
            if downloaded_count > 0 and downloaded_count % 60 == 0:
                print("♻️ Restarting browser to free memory...")
                await context.close()
                await browser.close()
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(accept_downloads=True)
                page = await context.new_page()
                await page.goto(
                    "https://signal.mutationalsignatures.com/", timeout=60000
                )
                await page.wait_for_load_state("networkidle")

        await browser.close()

    print(f"Work completed: {work_dir}")
    return work_dir


if __name__ == "__main__":
    test_work_id = str(uuid.uuid4())

    filename = "pcawg_ids_matched_DonorID_20251008_183516.csv"
    upload_path = Path(__file__).resolve().parents[1] / "uploads" / filename

    mapping = load_mapping_from_filename(upload_path)
    ids = list(mapping.keys())  # List of Donor IDs

    # Run scraper
    work_dir = asyncio.run(scrape_signal(ids, work_id=test_work_id))

    # Process downloaded CSVs
    destructure_csvs(work_dir, mapping)
    print("All done.")
