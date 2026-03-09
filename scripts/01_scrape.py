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

BASE_URL      = "https://www.diputados.gob.mx"
LEYES_BASE    = f"{BASE_URL}/LeyesBiblio"
INDEX_URL     = f"{LEYES_BASE}/index.htm"

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_DELAY_SECONDS = 1.5   # Polite delay between file downloads
REQUEST_TIMEOUT       = 60    # .doc files can be large
MAX_RETRIES           = 3

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


def abs_url(href: str) -> str:
    """
    Turn any href found on the index page into an absolute URL.

    The index page lives at /LeyesBiblio/index.htm, so relative hrefs
    like 'ref/cpeum.htm' or 'doc/CPEUM.doc' are relative to /LeyesBiblio/.
    Hrefs starting with '/' are relative to the domain root.
    Hrefs starting with 'http' are already absolute.
    """
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    # Relative to /LeyesBiblio/
    return f"{LEYES_BASE}/{href}"


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

    Table structure (confirmed 2026-03-09):
        Col 0 — row number (001, 002, …)
        Col 1 — law name as <a href="ref/xxx.htm"> (NO leading slash, relative)
                 also contains DOF publication date and abrogation notice
        Col 2 — Última Reforma date text
        Col 3 — TEXTO VIGENTE: icon links to pdf/XXX.pdf, doc/XXX.doc, pdf_mov/...

    Key fix: hrefs are RELATIVE (e.g. 'ref/cpeum.htm', 'doc/CPEUM.doc'),
    NOT absolute paths ('/LeyesBiblio/ref/cpeum.htm').
    The abs_url() helper resolves them correctly.
    """
    soup = BeautifulSoup(html, "lxml")
    laws: list[dict] = []
    seen_file_ids: set[str] = set()

    # The main table has 320 rows and no <th> tags — just pick the largest table.
    all_tables = soup.find_all("table")
    if not all_tables:
        log.error("No <table> tags found on the page at all.")
        return laws

    main_table = max(all_tables, key=lambda t: len(t.find_all("tr")))
    rows = main_table.find_all("tr")
    log.info(f"Scanning {len(rows)} rows in the main table …")

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        # ----------------------------------------------------------------
        # Col 1 — law name cell: look for relative ref/xxx.htm or abro/xxx.htm
        # ----------------------------------------------------------------
        name_cell = cells[1]
        # FIX: match relative hrefs — no leading slash required
        ref_link = name_cell.find(
            "a", href=re.compile(r"^(ref|abro)/[^/]+\.htm$", re.IGNORECASE)
        )
        if ref_link is None:
            continue

        ref_href = ref_link["href"].strip()   # e.g. 'ref/cpeum.htm'
        stem_match = re.search(r"(ref|abro)/([^/]+)\.htm$", ref_href, re.IGNORECASE)
        if not stem_match:
            continue

        file_id = stem_match.group(2).upper()   # e.g. 'CPEUM'
        if file_id in seen_file_ids:
            continue
        seen_file_ids.add(file_id)

        ref_url = abs_url(ref_href)

        # ----------------------------------------------------------------
        # Col 3 — TEXTO VIGENTE: grab doc and pdf URLs directly from here
        # ----------------------------------------------------------------
        doc_url = pdf_url = ""
        if len(cells) >= 4:
            links_cell3 = cells[3].find_all("a", href=True)
            for a in links_cell3:
                h = a["href"].strip()
                if re.search(r"\.doc$", h, re.IGNORECASE) and not re.search(r"pdf_mov", h, re.IGNORECASE):
                    doc_url = abs_url(h)
                elif re.search(r"\.pdf$", h, re.IGNORECASE) and not re.search(r"pdf_mov", h, re.IGNORECASE):
                    pdf_url = abs_url(h)

        # Fallback: construct the classic URL from file_id
        if not doc_url:
            doc_url = f"{LEYES_BASE}/doc/{file_id}.doc"
        if not pdf_url:
            pdf_url = f"{LEYES_BASE}/pdf/{file_id}.pdf"

        # ----------------------------------------------------------------
        # Col 0 — row number
        # ----------------------------------------------------------------
        number = cells[0].get_text(strip=True)

        # ----------------------------------------------------------------
        # Col 1 — law name, DOF publication date, abrogation
        # ----------------------------------------------------------------
        bold = name_cell.find(["b", "strong"])
        name = bold.get_text(strip=True) if bold else ref_link.get_text(strip=True)

        cell_text = name_cell.get_text(" ", strip=True)

        dof_match = re.search(r"DOF\s+\d{2}/\d{2}/\d{4}", cell_text)
        dof_pub   = dof_match.group(0) if dof_match else ""

        abroga_match = re.search(
            r"\(Abroga[dr][ao][^)]*\)|Abrogad[ao]\s+[^(]+",
            cell_text, re.IGNORECASE,
        )
        is_abrogated    = bool(abroga_match)
        abrogation_note = abroga_match.group(0).strip() if abroga_match else None

        # ----------------------------------------------------------------
        # Col 2 — Última Reforma
        # ----------------------------------------------------------------
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
            "ref_url":         ref_url,
            "doc_url":         doc_url,
            "pdf_url":         pdf_url,
        })

    laws.sort(key=lambda x: x.get("number", "999"))
    log.info(f"Parsed {len(laws)} laws from index")
    return laws


# ---------------------------------------------------------------------------
# .doc download
# ---------------------------------------------------------------------------

def doc_already_downloaded(file_id: str) -> tuple[bool, str | None]:
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
    file_id  = law["file_id"]
    doc_url  = law["doc_url"]
    doc_path = RAW_DIR / f"{file_id}.doc"

    already, _ = doc_already_downloaded(file_id)
    if already:
        log.info(f"  → Already downloaded, skipping")
        return True

    log.info(f"  Downloading {doc_url}")
    resp = fetch_with_retry(doc_url, session, stream=True)
    if resp is None:
        return False

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

    meta = {
        **law,
        "scraped_at":     datetime.now(timezone.utc).isoformat(),
        "doc_checksum":   checksum,
        "doc_size_bytes": bytes_written,
        "doc_path":       str(doc_path.relative_to(RAW_DIR.parent)),
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
    log.info("Fetching law index …")
    resp = fetch_with_retry(INDEX_URL, session)
    if resp is None:
        log.error("Cannot fetch index. Check your internet connection.")
        sys.exit(1)

    # Trust the Content-Type header for encoding (page is ISO-8859-1)
    encoding = resp.encoding or "latin-1"
    html = resp.content.decode(encoding, errors="replace")

    laws = parse_index_html(html)
    if not laws:
        log.error(
            "No laws found in the index. The page structure may have changed.\n"
            "Run diagnose_scraper.py and inspect the output."
        )
        sys.exit(1)

    log.info(f"Found {len(laws)} laws in the index")

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
        file_id    = law["file_id"]
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
            stub = {**law, "scraped_at": None, "doc_checksum": None, "download_failed": True}
            stub_path = RAW_DIR / f"{file_id}.json"
            with open(stub_path, "w", encoding="utf-8") as f:
                json.dump(stub, f, ensure_ascii=False, indent=2)

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