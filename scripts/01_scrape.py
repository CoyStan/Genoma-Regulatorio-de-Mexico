#!/usr/bin/env python3
"""
01_scrape.py — Scrape all federal laws from diputados.gob.mx/LeyesBiblio

Output: data/raw/<law_id>.json for each law scraped.

Each output file contains:
    {
        "id": "ley-federal-del-trabajo",
        "name": "Ley Federal del Trabajo",
        "source_url": "https://...",
        "scraped_at": "2024-01-15T10:30:00Z",
        "html_checksum": "sha256:...",
        "html": "...",   # raw HTML of the law page
    }

Design principles:
    - Idempotent: skips laws already scraped (by checksum).
    - Polite: 1-2 second delay between requests.
    - Transparent: logs every success/failure.
    - Graceful degradation: if HTML fails, falls back to PDF URL.
"""

import hashlib
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://www.diputados.gob.mx"
INDEX_URL = f"{BASE_URL}/LeyesBiblio/index.htm"
FALLBACK_INDEX_URL = "https://mexico.justia.com/federales/leyes/"

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_DELAY_SECONDS = 1.5  # Be respectful to the server
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": (
        "GenomRegulatorioMX/1.0 (civic tech; open data; "
        "https://github.com/quetzali-rg/genoma-regulatorio-mx; "
        "contact: open-source@example.com)"
    ),
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(RAW_DIR.parent / "scrape.log", mode="a"),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def sha256_checksum(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return "sha256:" + hashlib.sha256(content).hexdigest()


def slugify(name: str) -> str:
    """Convert a law name to a filesystem-safe slug."""
    name = name.lower().strip()
    name = re.sub(r"[áàä]", "a", name)
    name = re.sub(r"[éèë]", "e", name)
    name = re.sub(r"[íìï]", "i", name)
    name = re.sub(r"[óòö]", "o", name)
    name = re.sub(r"[úùü]", "u", name)
    name = re.sub(r"ñ", "n", name)
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"-+", "-", name)
    return name.strip("-")


def fetch_with_retry(url: str, session: requests.Session) -> requests.Response | None:
    """Fetch a URL with exponential backoff retry logic."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            log.warning(f"HTTP {e.response.status_code} for {url} (attempt {attempt}/{MAX_RETRIES})")
        except requests.RequestException as e:
            log.warning(f"Request failed for {url}: {e} (attempt {attempt}/{MAX_RETRIES})")

        if attempt < MAX_RETRIES:
            wait = 2 ** attempt
            log.info(f"Retrying in {wait}s...")
            time.sleep(wait)

    log.error(f"All {MAX_RETRIES} attempts failed for {url}")
    return None


def already_scraped(law_id: str, checksum: str | None = None) -> bool:
    """
    Return True if this law has already been scraped.
    If checksum is provided, also verify the content hasn't changed.
    """
    output_path = RAW_DIR / f"{law_id}.json"
    if not output_path.exists():
        return False
    if checksum is None:
        return True
    try:
        with open(output_path) as f:
            existing = json.load(f)
        return existing.get("html_checksum") == checksum
    except Exception:
        return False


def save_law(data: dict) -> None:
    """Save a scraped law to data/raw/<law_id>.json."""
    output_path = RAW_DIR / f"{data['id']}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"Saved: {output_path.name} ({len(data.get('html', ''))//1024}KB)")


# ---------------------------------------------------------------------------
# Index scraping
# ---------------------------------------------------------------------------

def scrape_law_index(session: requests.Session) -> list[dict]:
    """
    Scrape the law index from diputados.gob.mx/LeyesBiblio.
    Returns a list of dicts: [{name, url, pdf_url, ...}, ...]
    """
    log.info(f"Fetching law index from {INDEX_URL}")
    response = fetch_with_retry(INDEX_URL, session)
    if response is None:
        log.error("Could not fetch law index. Aborting.")
        sys.exit(1)

    soup = BeautifulSoup(response.text, "html.parser")
    laws = []

    # The diputados.gob.mx index page lists laws in a table.
    # Each row has: law name (link to HTML), DOC link, PDF link.
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        # First cell: law name and HTML link
        name_cell = cells[0]
        link = name_cell.find("a", href=True)
        if not link:
            continue

        name = link.get_text(strip=True)
        if not name or len(name) < 5:
            continue

        href = link["href"]
        # Normalize URL
        if href.startswith("http"):
            html_url = href
        else:
            html_url = f"{BASE_URL}/LeyesBiblio/{href.lstrip('/')}"

        # Look for PDF link in other cells
        pdf_url = None
        for cell in cells[1:]:
            pdf_link = cell.find("a", href=re.compile(r"\.pdf$", re.IGNORECASE))
            if pdf_link:
                pdf_href = pdf_link["href"]
                if pdf_href.startswith("http"):
                    pdf_url = pdf_href
                else:
                    pdf_url = f"{BASE_URL}/LeyesBiblio/{pdf_href.lstrip('/')}"
                break

        law_id = slugify(name)
        if law_id:
            laws.append({
                "id": law_id,
                "name": name,
                "html_url": html_url,
                "pdf_url": pdf_url,
            })

    log.info(f"Found {len(laws)} laws in index")
    return laws


# ---------------------------------------------------------------------------
# Law page scraping
# ---------------------------------------------------------------------------

def scrape_law_page(law_info: dict, session: requests.Session) -> dict | None:
    """
    Scrape a single law's HTML page.
    Returns structured data or None if scraping failed.
    """
    url = law_info["html_url"]
    response = fetch_with_retry(url, session)
    if response is None:
        return None

    # Detect encoding (diputados.gob.mx sometimes serves Latin-1)
    try:
        html = response.content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            html = response.content.decode("latin-1")
        except UnicodeDecodeError:
            html = response.text

    checksum = sha256_checksum(html)

    # Skip if already scraped with same content
    if already_scraped(law_info["id"], checksum):
        log.info(f"Skipping {law_info['id']} (unchanged)")
        return None

    return {
        "id": law_info["id"],
        "name": law_info["name"],
        "source_url": url,
        "pdf_url": law_info.get("pdf_url"),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "html_checksum": checksum,
        "html": html,
    }


# ---------------------------------------------------------------------------
# Manual law list (fallback / supplement)
# ---------------------------------------------------------------------------

KNOWN_LAWS_MANUAL = [
    {
        "id": "constitucion-politica",
        "name": "Constitución Política de los Estados Unidos Mexicanos",
        "html_url": "https://www.diputados.gob.mx/LeyesBiblio/htm/CPEUM.htm",
        "pdf_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CPEUM.pdf",
    },
    {
        "id": "ley-federal-del-trabajo",
        "name": "Ley Federal del Trabajo",
        "html_url": "https://www.diputados.gob.mx/LeyesBiblio/htm/LFT.htm",
        "pdf_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf",
    },
    {
        "id": "ley-del-seguro-social",
        "name": "Ley del Seguro Social",
        "html_url": "https://www.diputados.gob.mx/LeyesBiblio/htm/LSS.htm",
        "pdf_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LSS.pdf",
    },
    {
        "id": "codigo-fiscal-federacion",
        "name": "Código Fiscal de la Federación",
        "html_url": "https://www.diputados.gob.mx/LeyesBiblio/htm/CFF.htm",
        "pdf_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CFF.pdf",
    },
    {
        "id": "ley-isr",
        "name": "Ley del Impuesto sobre la Renta",
        "html_url": "https://www.diputados.gob.mx/LeyesBiblio/htm/LISR.htm",
        "pdf_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LISR.pdf",
    },
    {
        "id": "codigo-penal-federal",
        "name": "Código Penal Federal",
        "html_url": "https://www.diputados.gob.mx/LeyesBiblio/htm/CPF.htm",
        "pdf_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CPF.pdf",
    },
    {
        "id": "ley-general-salud",
        "name": "Ley General de Salud",
        "html_url": "https://www.diputados.gob.mx/LeyesBiblio/htm/LGS.htm",
        "pdf_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGS.pdf",
    },
    {
        "id": "codigo-civil-federal",
        "name": "Código Civil Federal",
        "html_url": "https://www.diputados.gob.mx/LeyesBiblio/htm/CCF.htm",
        "pdf_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CCF.pdf",
    },
    {
        "id": "lgeepa",
        "name": "Ley General del Equilibrio Ecológico y la Protección al Ambiente",
        "html_url": "https://www.diputados.gob.mx/LeyesBiblio/htm/LGEEPA.htm",
        "pdf_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGEEPA.pdf",
    },
    {
        "id": "lgtaip",
        "name": "Ley General de Transparencia y Acceso a la Información Pública",
        "html_url": "https://www.diputados.gob.mx/LeyesBiblio/htm/LGTAIP.htm",
        "pdf_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGTAIP.pdf",
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=== 01_scrape.py — Genoma Regulatorio de México ===")
    log.info(f"Scrape date: {datetime.now(timezone.utc).isoformat()}")
    log.info(f"Output directory: {RAW_DIR}")

    session = requests.Session()
    session.headers.update(HEADERS)

    # Try to get the full index from diputados.gob.mx
    law_list = scrape_law_index(session)

    # Merge with manual list (dedup by id, manual takes precedence for URL)
    manual_ids = {law["id"] for law in KNOWN_LAWS_MANUAL}
    law_list = [law for law in law_list if law["id"] not in manual_ids]
    law_list = KNOWN_LAWS_MANUAL + law_list

    log.info(f"Total laws to scrape: {len(law_list)}")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, law_info in enumerate(law_list, 1):
        log.info(f"[{i}/{len(law_list)}] {law_info['name'][:60]}")

        # Quick check: skip if already scraped
        if already_scraped(law_info["id"]):
            log.info(f"  → Already scraped, skipping")
            skip_count += 1
            continue

        result = scrape_law_page(law_info, session)
        if result is None:
            # Could be unchanged (checksum match) or a failure
            if (RAW_DIR / f"{law_info['id']}.json").exists():
                skip_count += 1
            else:
                fail_count += 1
        else:
            save_law(result)
            success_count += 1

        # Polite delay between requests
        if i < len(law_list):
            time.sleep(REQUEST_DELAY_SECONDS)

    log.info(f"\n=== Scraping complete ===")
    log.info(f"  Scraped: {success_count}")
    log.info(f"  Skipped (cached): {skip_count}")
    log.info(f"  Failed: {fail_count}")
    log.info(f"  Output: {RAW_DIR}")


if __name__ == "__main__":
    main()
