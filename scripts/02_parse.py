#!/usr/bin/env python3
"""
02_parse.py — Parse raw scraped HTML into structured law JSON.

Reads: data/raw/<law_id>.json
Writes: data/processed/<law_id>.json

Each processed file contains:
    {
        "id": "ley-federal-del-trabajo",
        "name": "Ley Federal del Trabajo",
        "short_name": "LFT",
        "year_enacted": 1970,
        "year_last_reform": 2023,
        "category": "trabajo",
        "source_url": "https://...",
        "full_text": "...",  # cleaned plaintext, no HTML
        "articles": [
            {
                "number": "1",
                "title": "Artículo 1",
                "text": "...",
            },
            ...
        ],
        "num_articles": 1010,
        "processed_at": "2024-01-15T11:00:00Z",
    }
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.lookup import CANONICAL_LAWS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Article parsing
# ---------------------------------------------------------------------------

# Patterns for detecting article headings in Mexican legal text
ARTICLE_HEADING_PATTERNS = [
    re.compile(r"^Art[ií]culo\s+(\d+[\w\-]*)\s*[.\-–]?\s*(.*)$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^ARTÍCULO\s+(\d+[\w\-]*)\s*[.\-–]?\s*(.*)$", re.MULTILINE),
    re.compile(r"^Art\.\s+(\d+[\w\-]*)\s*[.\-–]?\s*(.*)$", re.IGNORECASE | re.MULTILINE),
]

# Year patterns for detecting enactment/reform dates
YEAR_PATTERN = re.compile(r"\b(19[4-9]\d|20[0-2]\d)\b")
REFORM_PATTERN = re.compile(
    r"Última\s+reforma\s+publicada.*?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})",
    re.IGNORECASE,
)
PUBLISHED_PATTERN = re.compile(
    r"publicada?\s+en\s+el\s+D\.O\.F\.\s+.*?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})",
    re.IGNORECASE,
)

MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def parse_spanish_date(date_str: str) -> int | None:
    """Extract year from a Spanish date string like '1 de enero de 1970'."""
    match = re.search(r"\b(\d{4})\b", date_str)
    return int(match.group(1)) if match else None


def html_to_text(html: str) -> str:
    """
    Convert HTML to clean plaintext, preserving article structure.
    Removes navigation, scripts, styles, and other non-content elements.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "meta", "link", "noscript", "iframe"]):
        tag.decompose()

    # Remove common navigation patterns in diputados.gob.mx
    for tag in soup.find_all(class_=re.compile(r"nav|menu|header|footer|breadcrumb", re.IGNORECASE)):
        tag.decompose()

    # Get text, preserving newlines at block elements
    lines = []
    for element in soup.find_all(["p", "div", "td", "li", "h1", "h2", "h3", "h4", "br"]):
        text = element.get_text(separator=" ", strip=True)
        if text:
            lines.append(text)

    full_text = "\n".join(lines)

    # Clean up excessive whitespace
    full_text = re.sub(r"[ \t]+", " ", full_text)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    full_text = full_text.strip()

    return full_text


def extract_articles(text: str) -> list[dict]:
    """
    Parse the full text into individual articles.
    Returns list of {number, title, text} dicts.
    """
    articles = []
    current_article = None
    current_lines = []

    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            if current_lines:
                current_lines.append("")
            continue

        # Check if this line starts a new article
        article_match = None
        for pattern in ARTICLE_HEADING_PATTERNS:
            m = pattern.match(line)
            if m:
                article_match = m
                break

        if article_match:
            # Save previous article
            if current_article is not None:
                article_text = "\n".join(current_lines).strip()
                articles.append({
                    "number": current_article["number"],
                    "title": current_article["title"],
                    "text": article_text,
                })

            article_num = article_match.group(1)
            article_title = article_match.group(2).strip() if article_match.lastindex >= 2 else ""
            current_article = {
                "number": article_num,
                "title": f"Artículo {article_num}" + (f" — {article_title}" if article_title else ""),
            }
            current_lines = [line]
        else:
            if current_article is not None:
                current_lines.append(line)

    # Don't forget the last article
    if current_article is not None and current_lines:
        articles.append({
            "number": current_article["number"],
            "title": current_article["title"],
            "text": "\n".join(current_lines).strip(),
        })

    return articles


def extract_metadata(text: str, law_id: str) -> dict:
    """
    Extract metadata (year enacted, year last reform, etc.) from the law text.
    Falls back to the canonical lookup table for known laws.
    """
    metadata = {}

    # Try to extract year of last reform
    reform_match = REFORM_PATTERN.search(text)
    if reform_match:
        year = parse_spanish_date(reform_match.group(1))
        if year:
            metadata["year_last_reform"] = year

    # Try to extract publication year
    published_match = PUBLISHED_PATTERN.search(text)
    if published_match:
        year = parse_spanish_date(published_match.group(1))
        if year:
            metadata["year_enacted"] = year

    # Find all years in the text, take the earliest as enactment year
    if "year_enacted" not in metadata:
        years_found = [int(y) for y in YEAR_PATTERN.findall(text[:2000]) if 1917 <= int(y) <= 2024]
        if years_found:
            metadata["year_enacted"] = min(years_found)

    # Supplement with canonical lookup data
    canonical = CANONICAL_LAWS.get(law_id, {})
    metadata["short_name"] = canonical.get("short", "")
    metadata["category"] = canonical.get("sector", "")

    return metadata


# ---------------------------------------------------------------------------
# Main processing function
# ---------------------------------------------------------------------------

def process_law(raw_path: Path) -> dict | None:
    """
    Process a single raw law JSON file into structured format.
    Returns the processed dict or None if processing failed.
    """
    try:
        with open(raw_path, encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.error(f"Cannot read {raw_path}: {e}")
        return None

    law_id = raw.get("id", raw_path.stem)
    html = raw.get("html", "")

    if not html:
        log.warning(f"No HTML content for {law_id}")
        return None

    log.info(f"Processing {law_id} ({len(html)//1024}KB HTML)")

    # Convert HTML to text
    full_text = html_to_text(html)
    if not full_text:
        log.warning(f"Empty text after parsing for {law_id}")
        return None

    # Extract articles
    articles = extract_articles(full_text)
    log.info(f"  → {len(articles)} articles extracted")

    # Extract metadata
    metadata = extract_metadata(full_text, law_id)

    processed = {
        "id": law_id,
        "name": raw.get("name", ""),
        "short_name": metadata.get("short_name", ""),
        "year_enacted": metadata.get("year_enacted"),
        "year_last_reform": metadata.get("year_last_reform"),
        "category": metadata.get("category", ""),
        "source_url": raw.get("source_url", ""),
        "pdf_url": raw.get("pdf_url"),
        "full_text": full_text,
        "articles": articles,
        "num_articles": len(articles),
        "char_count": len(full_text),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "scrape_checksum": raw.get("html_checksum", ""),
    }

    return processed


def save_processed(data: dict) -> None:
    output_path = PROCESSED_DIR / f"{data['id']}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"  → Saved: {output_path.name}")


def already_processed(law_id: str, scrape_checksum: str) -> bool:
    """Return True if this version of the law has already been processed."""
    output_path = PROCESSED_DIR / f"{law_id}.json"
    if not output_path.exists():
        return False
    try:
        with open(output_path) as f:
            existing = json.load(f)
        return existing.get("scrape_checksum") == scrape_checksum
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=== 02_parse.py — Genoma Regulatorio de México ===")

    raw_files = sorted(RAW_DIR.glob("*.json"))
    if not raw_files:
        log.error(f"No raw files found in {RAW_DIR}. Run 01_scrape.py first.")
        sys.exit(1)

    log.info(f"Found {len(raw_files)} raw law files to process")

    success = 0
    skip = 0
    fail = 0

    for i, raw_path in enumerate(raw_files, 1):
        log.info(f"[{i}/{len(raw_files)}] {raw_path.name}")

        # Load just enough to check checksum
        try:
            with open(raw_path) as f:
                raw_meta = json.load(f)
        except Exception as e:
            log.error(f"Cannot read {raw_path}: {e}")
            fail += 1
            continue

        law_id = raw_meta.get("id", raw_path.stem)
        checksum = raw_meta.get("html_checksum", "")

        if already_processed(law_id, checksum):
            log.info(f"  → Skipping (already processed, checksum match)")
            skip += 1
            continue

        result = process_law(raw_path)
        if result:
            save_processed(result)
            success += 1
        else:
            fail += 1

    log.info(f"\n=== Parsing complete ===")
    log.info(f"  Processed: {success}")
    log.info(f"  Skipped: {skip}")
    log.info(f"  Failed: {fail}")


if __name__ == "__main__":
    main()
