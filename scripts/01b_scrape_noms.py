#!/usr/bin/env python3
"""
01b_scrape_noms.py — Scrape Normas Oficiales Mexicanas from DOF.

Source: https://diariooficial.gob.mx/normasOficiales.php?codp=N&view=si
Strategy: iterate codp integers from START to END, keep only:
  - Title starts with "NOM-" (excludes PROY-NOM, NOM-EM, NOM-A)
  - Not explicitly marked as cancelled/abrogated in the page
  - De-duplicate by NOM code, keeping latest codp (most recent version)

Writes:
  data/raw_noms/<nom_id>.html       — raw page HTML
  data/raw_noms/_index.json         — index of all scraped NOMs
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL    = "https://diariooficial.gob.mx/normasOficiales.php"
CODP_START  = 4000   # ~2013
CODP_END    = 9700   # covers through 2025; extend if needed
DELAY       = 1.2    # seconds between requests (polite)
TIMEOUT     = 20
RAW_DIR     = Path(__file__).parent.parent / "data" / "raw_noms"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# NOM title must start with "NOM-" followed by digits
NOM_TITLE_RE = re.compile(r"^NOM-\d+", re.IGNORECASE)

# Cancellation signals in page text
CANCELLED_RE = re.compile(
    r"\b(?:cancelad[ao]|abrogad[ao]|sin\s+vigencia|deja(?:\s+de)?\s+estar\s+en\s+vigor)\b",
    re.IGNORECASE,
)

# Extract NOM code from title: "NOM-043-SSA2-2012 ..." → "NOM-043-SSA2-2012"
NOM_CODE_RE = re.compile(r"(NOM-[\w\d]+-[\w\d]+-\d{4})", re.IGNORECASE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

session = requests.Session()
session.headers.update({"User-Agent": "GenomaNormativo/1.0 (research; contacto@example.com)"})


# ── Helpers ───────────────────────────────────────────────────────────────────

def slugify(nom_code: str) -> str:
    return nom_code.lower().replace(" ", "-")


def fetch_nom_page(codp: int) -> tuple[str | None, str | None]:
    """Fetch a NOM page. Returns (html, final_url) or (None, None) on failure."""
    url = f"{BASE_URL}?codp={codp}&view=si"
    try:
        resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        if resp.status_code != 200:
            return None, None
        # DOF sometimes returns a redirect to the index when codp is invalid
        if "normasOficiales.php" in resp.url and "codp" not in resp.url:
            return None, None
        return resp.text, resp.url
    except requests.RequestException:
        return None, None


def extract_nom_metadata(html: str, codp: int) -> dict | None:
    """
    Parse a DOF NOM page and extract metadata.
    Returns dict or None if page is not a valid active NOM.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Try to find the NOM title — DOF pages use <h1> or the first bold heading
    title = ""
    for tag in soup.find_all(["h1", "h2", "b", "strong"]):
        text = tag.get_text(" ", strip=True)
        if NOM_TITLE_RE.match(text):
            title = text
            break

    if not title:
        # Fallback: look in the full page text
        page_text = soup.get_text(" ")
        m = NOM_CODE_RE.search(page_text)
        if not m:
            return None
        title = m.group(1)

    # Must match NOM- pattern
    if not NOM_TITLE_RE.match(title):
        return None

    # Extract canonical NOM code
    code_match = NOM_CODE_RE.search(title)
    if not code_match:
        return None
    nom_code = code_match.group(1).upper()

    # Check for cancellation signals in the first 2000 chars of body text
    body_text = soup.get_text(" ")[:3000]
    if CANCELLED_RE.search(body_text):
        log.debug(f"  codp={codp}: {nom_code} — marked as cancelled, skipping")
        return None

    # Extract ministry from NOM code: NOM-043-SSA2-2012 → SSA2
    parts = nom_code.split("-")
    ministry = parts[2] if len(parts) >= 3 else "unknown"
    year_str = parts[-1] if parts[-1].isdigit() else ""
    year = int(year_str) if year_str else None

    # Only include NOMs from 2013 onwards (when DOF digital system starts)
    if year and year < 2013:
        return None

    return {
        "codp":     codp,
        "nom_code": nom_code,
        "nom_id":   slugify(nom_code),
        "title":    title,
        "ministry": ministry,
        "year":     year,
        "source_url": f"{BASE_URL}?codp={codp}&view=si",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=== 01b_scrape_noms.py — Genoma Regulatorio de México ===")
    log.info(f"Scanning codp {CODP_START}–{CODP_END} ({CODP_END - CODP_START} requests)")
    log.info(f"Estimated time: {(CODP_END - CODP_START) * DELAY / 3600:.1f} hours")

    # Load existing index to allow resuming
    index_path = RAW_DIR / "_index.json"
    if index_path.exists():
        with open(index_path, encoding="utf-8") as f:
            index: dict[str, dict] = json.load(f)
        log.info(f"Resuming — {len(index)} NOMs already indexed")
    else:
        index = {}  # nom_code → metadata

    # Track which codp values we've already processed
    processed_codps: set[int] = set()
    for meta in index.values():
        processed_codps.add(meta["codp"])
    # Also check raw HTML files for codp hints
    for html_file in RAW_DIR.glob("*.html"):
        # We can't recover codp from filename alone — just skip already-saved noms
        pass

    found = 0
    skipped_invalid = 0
    skipped_cached = 0

    for codp in range(CODP_START, CODP_END + 1):
        if codp in processed_codps:
            skipped_cached += 1
            continue

        html, url = fetch_nom_page(codp)
        time.sleep(DELAY)

        if not html:
            skipped_invalid += 1
            continue

        meta = extract_nom_metadata(html, codp)
        if not meta:
            skipped_invalid += 1
            continue

        nom_id  = meta["nom_id"]
        nom_code = meta["nom_code"]

        # De-duplicate: if we already have this NOM code, keep the latest codp
        if nom_code in index:
            existing_codp = index[nom_code]["codp"]
            if codp > existing_codp:
                log.info(f"  codp={codp}: {nom_code} — newer version, replacing codp={existing_codp}")
                old_html = RAW_DIR / f"{index[nom_code]['nom_id']}.html"
                if old_html.exists():
                    old_html.unlink()
            else:
                log.debug(f"  codp={codp}: {nom_code} — older than existing, skipping")
                skipped_invalid += 1
                continue

        # Save raw HTML
        html_path = RAW_DIR / f"{nom_id}.html"
        html_path.write_text(html, encoding="utf-8")

        index[nom_code] = meta
        found += 1

        log.info(f"  [{found}] codp={codp}: {nom_code} ({meta['ministry']}, {meta['year']})")

        # Save index periodically
        if found % 50 == 0:
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
            log.info(f"  Index saved ({len(index)} NOMs so far)")

    # Final index save
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    log.info(f"\n=== Scraping complete ===")
    log.info(f"  NOMs found: {found}")
    log.info(f"  Invalid/not-NOM codp values: {skipped_invalid}")
    log.info(f"  Already cached: {skipped_cached}")
    log.info(f"  Total in index: {len(index)}")
    log.info(f"  Index: {index_path}")


if __name__ == "__main__":
    main()
