import os
import re
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
from typing import Dict

OUTPUT_DIR = Path("/tmp/scraper_results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def _safe_filename(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\-_. ]+", "_", s)
    return s[:100]

def call_black_box(payload: Dict) -> str:
    """
    Función sincrónica 'caja negra' que hace scraping y guarda un resultado en disco.
    Retorna la ruta al archivo con el resultado.
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

    # Petición HTTP bloqueante (httpx.Client es sincrónico)
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        text = resp.text

    # Parseo con BeautifulSoup
    soup = BeautifulSoup(text, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "no-title"

    # Puedes extraer más cosas según necesites
    # ejemplo: todos los h1
    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]

    # Guardar resultado (JSON simple o texto)
    safe_name = _safe_filename(title)
    out_path = OUTPUT_DIR / f"{safe_name}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write(f"TITLE: {title}\n\n")
        f.write("H1s:\n")
        for h in h1s:
            f.write(f"- {h}\n")

    return str(out_path)
