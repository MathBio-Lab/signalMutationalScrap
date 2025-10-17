import threading
import asyncio
import uuid
from pathlib import Path

from app.integrations.test import load_mapping_from_filename, scrape_signal


def run_scraper_thread(ids, label):
    """Función que corre el scraper en su propio thread."""
    work_id = f"{label}_{uuid.uuid4()}"
    print(f"Starting thread {label} with {len(ids)} IDs...")
    work_dir = asyncio.run(scrape_signal(ids, work_id=work_id))
    print(f"Thread {label} completed: {work_dir}")


if __name__ == "__main__":
    filename = "pcawg_ids_matched_DonorID_20251008_183516.csv"
    upload_path = Path(__file__).resolve().parents[1] / "uploads" / filename

    mapping = load_mapping_from_filename(upload_path)
    ids = list(mapping.keys())

    half = len(ids) // 2
    ids_a = ids[:half]
    ids_b = ids[half:]

    t1 = threading.Thread(target=run_scraper_thread, args=(ids_a, "A"))
    t2 = threading.Thread(target=run_scraper_thread, args=(ids_b, "B"))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print("Both threads finished downloading.")
