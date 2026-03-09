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

    Table columns (current structure, 2025-2026):
        No. | LEY / Página de Reformas | Última Reforma | TEXTO VIGENTE (empty)

    The TEXTO VIGENTE column no longer contains direct .doc links.
    Each law name is now an <a href="/LeyesBiblio/ref/xxx.htm"> link.
    The actual .doc download link lives on that ref page (fetched in pass 2).

    Strategy:
      1. Scan rows for <a href=".../ref/xxx.htm"> or <a href=".../abro/xxx.htm">
      2. Derive file_id from the stem (e.g. "cpeum.htm" → "CPEUM")
      3. Record ref_url for the second-pass .doc URL resolution
    """
    soup = BeautifulSoup(html, "lxml")
    laws: list[dict] = []
    seen_file_ids: set[str] = set()

    # Find the main law table — look for a table that has a "No." or "LEY" header
    table = None
    for t in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in t.find_all("th")]
        if any("No" in h or "LEY" in h for h in headers):
            table = t
            break

    rows = table.find_all("tr") if table else soup.find_all("tr")
    log.info(f"Scanning {len(rows)} table rows for law links …")

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        name_cell = cells[1]

        # Law name links to /ref/xxx.htm (active) or /abro/xxx.htm (abrogated)
        ref_link = name_cell.find(
            "a", href=re.compile(r"/(ref|abro)/[^/]+\.htm$", re.IGNORECASE)
        )
        if ref_link is None:
            continue

        href = ref_link["href"].strip()
        stem_match = re.search(r"/(ref|abro)/([^/]+)\.htm$", href, re.IGNORECASE)
        if not stem_match:
            continue

        file_id = stem_match.group(2).upper()   # e.g. "CPEUM", "LFT"
        if file_id in seen_file_ids:
            continue
        seen_file_ids.add(file_id)

        # Absolute ref URL
        if href.startswith("http"):
            ref_url = href
        elif href.startswith("/"):
            ref_url = BASE_URL + href
        else:
            ref_url = f"{BASE_URL}/LeyesBiblio/{href}"

        # Classic download URLs — still tried as fallback if ref page lookup fails
        doc_url = f"{DOC_BASE_URL}/{file_id}.doc"
        pdf_url = f"{PDF_BASE_URL}/{file_id}.pdf"

        # ---- Column 0: row number ----
        number = cells[0].get_text(strip=True) if cells else ""

        # ---- Law name ----
        bold = name_cell.find(["b", "strong"])
        name = bold.get_text(strip=True) if bold else ref_link.get_text(strip=True)

        # ---- DOF publication date ----
        cell_text = name_cell.get_text(" ", strip=True)
        dof_match = re.search(r"DOF\s+\d{2}/\d{2}/\d{4}", cell_text)
        dof_pub = dof_match.group(0) if dof_match else ""

        # ---- Abrogation notice ----
        abroga_match = re.search(
            r"\(Abroga[dr][ao][^)]*\)|Abrogad[ao]\s+[^(]+",
            cell_text, re.IGNORECASE,
        )
        is_abrogated    = bool(abroga_match)
        abrogation_note = abroga_match.group(0).strip() if abroga_match else None

        # ---- Column 2: Última Reforma ----
        dof_reform = cells[2].get_text(" ", strip=True).strip() if len(cells) >= 3 else ""

        slug_id = slugify(name) if name and name != file_id else file_id.lower()

        laws.append({
            "file_id":         file_id,
            "id":              slug_id,
            "name":            name,
            "number":          number,
            "dof_published":   dof_pub,
            "dof_last_reform": dof_reform,
            "is_abrogated":    is_abrogated,
            "abrogation_note": abrogation_note,
            "ref_url":         ref_url,   # /ref/xxx.htm — used to find the real .doc link
            "doc_url":         doc_url,   # classic URL kept as fallback
            "pdf_url":         pdf_url,
        })

    laws.sort(key=lambda x: x.get("number", "999"))
    log.info(f"Parsed {len(laws)} laws from index")
    return laws


# ---------------------------------------------------------------------------
# Resolve the actual .doc URL from a law's ref page  (pass 2)
# ---------------------------------------------------------------------------

def resolve_doc_url(law: dict, session: requests.Session) -> str:
    """
    Fetch the law's /ref/xxx.htm page and extract the real .doc download link.

    Falls back to the classic constructed URL
    (e.g. /LeyesBiblio/doc/CPEUM.doc) if:
      - the ref page is unreachable, or
      - the ref page contains no .doc link.
    """
    ref_url  = law.get("ref_url", "")
    fallback = law["doc_url"]

    if not ref_url:
        return fallback

    resp = fetch_with_retry(ref_url, session)
    if resp is None:
        log.warning(f"  Could not fetch ref page {ref_url} — using classic URL")
        return fallback

    try:
        html = resp.content.decode("utf-8")
    except UnicodeDecodeError:
        html = resp.content.decode("latin-1")

    soup = BeautifulSoup(html, "lxml")
    doc_link = soup.find("a", href=re.compile(r"\.doc$", re.IGNORECASE))
    if doc_link:
        href = doc_link["href"].strip()
        if href.startswith("http"):
            return href
        if href.startswith("/"):
            return BASE_URL + href
        return f"{BASE_URL}/LeyesBiblio/{href}"

    log.warning(f"  No .doc link found on {ref_url} — using classic URL")
    return fallback


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
    doc_path = RAW_DIR / f"{file_id}.doc"

    # Quick existence check (without re-downloading)
    already, _ = doc_already_downloaded(file_id)
    if already:
        log.info(f"  → Already downloaded, skipping")
        return True

    # Resolve the real .doc URL from the law's ref page (two-pass scrape)
    doc_url = resolve_doc_url(law, session)
    # Store resolved URL back so it ends up in the metadata JSON
    law = {**law, "doc_url": doc_url}

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
            "Open the index in a browser and look for <a href='/ref/xxx.htm'> links\n"
            "in the law name column. Update parse_index_html() if the pattern changed."
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
