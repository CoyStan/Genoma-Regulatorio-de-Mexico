#!/usr/bin/env python3
"""
01_scrape.py — Scrape all federal laws from diputados.gob.mx/LeyesBiblio

The site no longer serves HTML versions of individual laws.
Each law is available as a .doc (Word) and .pdf file.

This script:
  1. Fetches the index page and parses the law table.
  2. Extracts metadata per law (number, name, DOF dates, abrogation status).
  3. Downloads the .doc file for each law.
  4. Saves a JSON metadata file alongside each .doc.

Output layout in data/raw/:
    CPEUM.doc          — raw Word document
    CPEUM.json         — metadata + index info
    LFT.doc
    LFT.json
    ...
    _index.json        — full scraped index (all laws, even if download failed)

Design principles:
    - Idempotent: skips .doc files already downloaded (SHA-256 checksum).
    - Polite: configurable delay between downloads.
    - Transparent: every skip/fail/success logged.
    - Resilient: exponential backoff on transient errors.
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

BASE_URL     = "https://www.diputados.gob.mx"
INDEX_URL    = f"{BASE_URL}/LeyesBiblio/index.htm"
DOC_BASE_URL = f"{BASE_URL}/LeyesBiblio/doc"
PDF_BASE_URL = f"{BASE_URL}/LeyesBiblio/pdf"

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_DELAY_SECONDS = 1.5   # Polite delay between file downloads
REQUEST_TIMEOUT       = 60    # .doc files can be large
MAX_RETRIES           = 3

# Use a browser-like User-Agent so the server doesn't reject us,
# plus identify the project for transparency.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GenomRegulatorioMX/1.0; "
        "+https://github.com/quetzali-rg/genoma-regulatorio-mx)"
    ),
    "Accept-Language": "es-MX,es;q=0.9",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(RAW_DIR.parent / "scrape.log", mode="a", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def slugify(name: str) -> str:
    """Convert a law name to a filesystem-safe lowercase slug with hyphens."""
    name = name.lower().strip()
    for src, dst in [
        ("á","a"),("à","a"),("ä","a"),
        ("é","e"),("è","e"),("ë","e"),
        ("í","i"),("ì","i"),("ï","i"),
        ("ó","o"),("ò","o"),("ö","o"),
        ("ú","u"),("ù","u"),("ü","u"),
        ("ñ","n"),
    ]:
        name = name.replace(src, dst)
    name = re.sub(r"[^a-z0-9\s\-]", "", name)
    name = re.sub(r"[\s\-]+", "-", name)
    return name.strip("-")


def fetch_with_retry(url: str, session: requests.Session, stream: bool = False):
    """GET with exponential-backoff retry. Returns Response or None."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT, stream=stream)
            resp.raise_for_status()
            return resp
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "?"
            log.warning(f"HTTP {code} — {url}  (attempt {attempt}/{MAX_RETRIES})")
        except requests.RequestException as exc:
            log.warning(f"Request error — {url}: {exc}  (attempt {attempt}/{MAX_RETRIES})")

        if attempt < MAX_RETRIES:
            wait = 2 ** attempt
            log.info(f"  Retrying in {wait}s …")
            time.sleep(wait)

    log.error(f"All {MAX_RETRIES} attempts failed: {url}")
    return None


# ---------------------------------------------------------------------------
# Index parsing
# ---------------------------------------------------------------------------

def parse_index_html(html: str) -> list[dict]:
    """
    Parse the LeyesBiblio index page into a list of law records.

    The page has a table with columns:
        No. | LEY / Página de Reformas | Última Reforma | TEXTO VIGENTE
                                                          (PDF icon, DOC icon, mobile icon)

    Strategy: find every <a href="...doc/XXX.doc"> link in the table,
    then walk up to the parent <tr> to extract the other columns.
    """
    soup = BeautifulSoup(html, "lxml")
    laws: list[dict] = []
    seen_file_ids: set[str] = set()

    # Find all links to .doc files anywhere in the page
    doc_links = soup.find_all("a", href=re.compile(r"/doc/[^/]+\.doc$", re.IGNORECASE))
    log.info(f"Found {len(doc_links)} .doc links on index page")

    for doc_link in doc_links:
        href = doc_link["href"].strip()

        # Normalise to absolute URL
        if href.startswith("http"):
            doc_url = href
        else:
            doc_url = BASE_URL + ("" if href.startswith("/") else "/") + href

        # Extract the file identifier, e.g. "CPEUM" from ".../doc/CPEUM.doc"
        file_id_match = re.search(r"/doc/([^/]+)\.doc$", doc_url, re.IGNORECASE)
        if not file_id_match:
            continue
        file_id = file_id_match.group(1)          # e.g. "CPEUM"
        if file_id in seen_file_ids:
            continue
        seen_file_ids.add(file_id)

        pdf_url = f"{PDF_BASE_URL}/{file_id}.pdf"

        # Walk up to the parent <tr> to grab other columns
        row = doc_link.find_parent("tr")
        if row is None:
            # Fallback: build a minimal record
            laws.append({
                "file_id":        file_id,
                "id":             file_id.lower(),
                "name":           file_id,
                "number":         "",
                "dof_published":  "",
                "dof_last_reform": "",
                "is_abrogated":   False,
                "abrogation_note": None,
                "doc_url":        doc_url,
                "pdf_url":        pdf_url,
            })
            continue

        cells = row.find_all("td")

        # ---- Column 0: row number (001, 002, …) ----
        number = cells[0].get_text(strip=True) if cells else ""

        # ---- Column 1: law name + DOF publication date ----
        name      = ""
        dof_pub   = ""
        is_abrogated  = False
        abrogation_note = None

        if len(cells) >= 2:
            name_cell = cells[1]

            # Law name is in <b> or <strong>
            bold = name_cell.find(["b", "strong"])
            if bold:
                name = bold.get_text(strip=True)
            else:
                # Fall back to all text in the cell, minus child links
                name = name_cell.get_text(" ", strip=True).split("\n")[0]

            # DOF publication date: look for "DOF DD/MM/YYYY" pattern
            cell_text = name_cell.get_text(" ", strip=True)
            dof_match = re.search(r"DOF\s+\d{2}/\d{2}/\d{4}", cell_text)
            if dof_match:
                dof_pub = dof_match.group(0)

            # Abrogation notice: "(Abrogado …)" or "Abrogada"
            abroga_match = re.search(
                r"\(Abroga[dr][ao][^)]*\)|Abrogad[ao]\s+[^(]+",
                cell_text,
                re.IGNORECASE,
            )
            if abroga_match:
                is_abrogated = True
                abrogation_note = abroga_match.group(0).strip()

        # ---- Column 2: Última Reforma date ----
        dof_reform = ""
        if len(cells) >= 3:
            reform_cell = cells[2]
            reform_text = reform_cell.get_text(" ", strip=True)
            # May say "DOF 03/03/2026" or "Notificación 17/06/2025 Sentencia SCJN"
            dof_reform = reform_text.strip()

        # Derive a slug from the file_id for use as the canonical law id.
        # We keep file_id in uppercase as the primary key (matches lookup.py short names).
        slug_id = slugify(name) if name and name != file_id else file_id.lower()

        laws.append({
            "file_id":         file_id,       # "CPEUM" — used to build download URLs
            "id":              slug_id,        # "constitucion-politica" style slug
            "name":            name,
            "number":          number,
            "dof_published":   dof_pub,
            "dof_last_reform": dof_reform,
            "is_abrogated":    is_abrogated,
            "abrogation_note": abrogation_note,
            "doc_url":         doc_url,
            "pdf_url":         pdf_url,
        })

    # Sort by row number for deterministic ordering
    laws.sort(key=lambda x: x.get("number", "999"))
    return laws


# ---------------------------------------------------------------------------
# .doc download
# ---------------------------------------------------------------------------

def doc_already_downloaded(file_id: str) -> tuple[bool, str | None]:
    """
    Return (already_done, existing_checksum).
    Checks both the .doc file and its metadata JSON.
    """
    doc_path  = RAW_DIR / f"{file_id}.doc"
    meta_path = RAW_DIR / f"{file_id}.json"
    if not doc_path.exists() or not meta_path.exists():
        return False, None
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        return True, meta.get("doc_checksum")
    except Exception:
        return False, None


def download_doc(law: dict, session: requests.Session) -> bool:
    """
    Download the .doc file for a law.
    Returns True on success, False on failure.
    Skips if the file already exists with the same content.
    """
    file_id  = law["file_id"]
    doc_url  = law["doc_url"]
    doc_path = RAW_DIR / f"{file_id}.doc"

    # Quick existence check (without re-downloading)
    already, _ = doc_already_downloaded(file_id)
    if already:
        log.info(f"  → Already downloaded, skipping")
        return True

    log.info(f"  Downloading {doc_url}")
    resp = fetch_with_retry(doc_url, session, stream=True)
    if resp is None:
        return False

    # Stream to disk
    bytes_written = 0
    try:
        with open(doc_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    bytes_written += len(chunk)
    except OSError as exc:
        log.error(f"  Write error for {doc_path}: {exc}")
        doc_path.unlink(missing_ok=True)
        return False

    checksum = sha256_of_file(doc_path)
    size_kb   = bytes_written // 1024

    log.info(f"  → {file_id}.doc saved ({size_kb} KB, {checksum[:20]}…)")

    # Save metadata JSON alongside the .doc
    meta = {
        **law,
        "scraped_at":   datetime.now(timezone.utc).isoformat(),
        "doc_checksum": checksum,
        "doc_size_bytes": bytes_written,
        "doc_path":     str(doc_path.relative_to(RAW_DIR.parent)),
    }
    meta_path = RAW_DIR / f"{file_id}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 60)
    log.info("01_scrape.py — Genoma Regulatorio de México")
    log.info(f"Date : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    log.info(f"Index: {INDEX_URL}")
    log.info(f"Out  : {RAW_DIR}")
    log.info("=" * 60)

    session = requests.Session()
    session.headers.update(HEADERS)

    # ------------------------------------------------------------------
    # Step 1: Fetch and parse the law index
    # ------------------------------------------------------------------
    log.info(f"Fetching law index …")
    resp = fetch_with_retry(INDEX_URL, session)
    if resp is None:
        log.error("Cannot fetch index. Check your internet connection.")
        sys.exit(1)

    # Detect encoding
    try:
        html = resp.content.decode("utf-8")
    except UnicodeDecodeError:
        html = resp.content.decode("latin-1")

    laws = parse_index_html(html)
    if not laws:
        log.error(
            "No laws found in the index. The page structure may have changed.\n"
            "Open the index in a browser and inspect the .doc download links."
        )
        sys.exit(1)

    log.info(f"Found {len(laws)} laws in the index")

    # Save the full index to disk for inspection / downstream use
    index_path = RAW_DIR / "_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "source_url": INDEX_URL,
                "total_laws": len(laws),
                "laws": laws,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    log.info(f"Index saved → {index_path}")

    # ------------------------------------------------------------------
    # Step 2: Download .doc files
    # ------------------------------------------------------------------
    success = skip = fail = 0

    for i, law in enumerate(laws, 1):
        file_id = law["file_id"]
        name_short = law["name"][:55] if law["name"] else file_id
        log.info(f"[{i:03d}/{len(laws)}] {file_id:12s}  {name_short}")

        already, _ = doc_already_downloaded(file_id)
        if already:
            log.info("  → cached")
            skip += 1
            continue

        ok = download_doc(law, session)
        if ok:
            success += 1
        else:
            fail += 1
            # Write a stub JSON so we know this law was seen but download failed
            stub = {**law, "scraped_at": None, "doc_checksum": None, "download_failed": True}
            stub_path = RAW_DIR / f"{file_id}.json"
            with open(stub_path, "w", encoding="utf-8") as f:
                json.dump(stub, f, ensure_ascii=False, indent=2)

        # Polite delay (skip after last item)
        if i < len(laws):
            time.sleep(REQUEST_DELAY_SECONDS)

    log.info("")
    log.info("=" * 60)
    log.info("Scraping complete")
    log.info(f"  Downloaded : {success}")
    log.info(f"  Skipped    : {skip}  (already cached)")
    log.info(f"  Failed     : {fail}")
    log.info(f"  Output     : {RAW_DIR}")
    log.info("=" * 60)

    if fail:
        log.warning(
            f"{fail} downloads failed. Check scrape.log for details. "
            "You can re-run the script — it will retry only failed files."
        )


if __name__ == "__main__":
    main()
