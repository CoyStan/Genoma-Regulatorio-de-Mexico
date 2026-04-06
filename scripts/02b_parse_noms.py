#!/usr/bin/env python3
"""
02b_parse_noms.py — Parse raw NOM HTML into structured JSON.

NOMs have a different structure than laws:
  - Numbered sections (1. Objetivo, 2. Campo de aplicación, 4. Definiciones...)
  - Subsections (4.1, 4.2, ...)
  - No "Artículo X" format

Reads:  data/raw_noms/<nom_id>.html
        data/raw_noms/_index.json
Writes: data/processed_noms/<nom_id>.json
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

RAW_DIR       = Path(__file__).parent.parent / "data" / "raw_noms"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed_noms"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Section heading patterns: "1.", "1.1", "1.1.1" followed by text
SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\s*[.\-\s]\s*(.*)$")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ── Parsing ───────────────────────────────────────────────────────────────────

def extract_sections(text: str) -> list[dict]:
    """
    Split NOM text into numbered sections.
    Falls back to treating the whole text as one section if no structure found.
    """
    sections = []
    current_num = None
    current_title = ""
    current_lines: list[str] = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            if current_lines:
                current_lines.append("")
            continue

        m = SECTION_RE.match(line)
        if m:
            # Save previous section
            if current_num is not None:
                sections.append({
                    "number": current_num,
                    "title":  current_title,
                    "text":   "\n".join(current_lines).strip(),
                })
            current_num   = m.group(1)
            current_title = m.group(2).strip()
            current_lines = [line]
        elif current_num is not None:
            current_lines.append(line)

    if current_num is not None and current_lines:
        sections.append({
            "number": current_num,
            "title":  current_title,
            "text":   "\n".join(current_lines).strip(),
        })

    # If no sections detected, treat as single blob
    if not sections and text.strip():
        sections = [{"number": "0", "title": "Texto completo", "text": text.strip()}]

    return sections


def parse_nom_html(html: str, meta: dict) -> dict | None:
    """Parse a NOM HTML page into structured JSON."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove navigation, headers, footers
    for tag in soup.find_all(["nav", "header", "footer", "script", "style"]):
        tag.decompose()

    # Extract main content area — DOF wraps content in a div with class or id
    content = (
        soup.find("div", {"id": "contenidoNorma"})
        or soup.find("div", {"class": re.compile(r"content|norma|texto", re.I)})
        or soup.find("body")
    )

    if not content:
        return None

    full_text = content.get_text("\n", strip=True)

    if len(full_text) < 100:
        return None

    sections = extract_sections(full_text)

    # Try to extract date from the page text
    date_re = re.compile(
        r"(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})",
        re.IGNORECASE,
    )
    date_match = date_re.search(full_text[:2000])
    publication_date = date_match.group(1) if date_match else None

    return {
        "id":               meta["nom_id"],
        "nom_code":         meta["nom_code"],
        "name":             meta["title"],
        "short_name":       meta["nom_code"],
        "ministry":         meta["ministry"],
        "year":             meta["year"],
        "publication_date": publication_date,
        "source_url":       meta["source_url"],
        "full_text":        full_text,
        "sections":         sections,
        "num_sections":     len(sections),
        "char_count":       len(full_text),
        "node_type":        "nom",
        "processed_at":     datetime.now(timezone.utc).isoformat(),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=== 02b_parse_noms.py — Genoma Regulatorio de México ===")

    index_path = RAW_DIR / "_index.json"
    if not index_path.exists():
        log.error("No _index.json found. Run 01b_scrape_noms.py first.")
        sys.exit(1)

    with open(index_path, encoding="utf-8") as f:
        index: dict[str, dict] = json.load(f)

    log.info(f"Parsing {len(index)} NOMs")

    success = skip = fail = 0

    for nom_code, meta in index.items():
        nom_id    = meta["nom_id"]
        html_path = RAW_DIR / f"{nom_id}.html"
        out_path  = PROCESSED_DIR / f"{nom_id}.json"

        if out_path.exists():
            skip += 1
            continue

        if not html_path.exists():
            log.warning(f"  Missing HTML for {nom_id}")
            fail += 1
            continue

        html = html_path.read_text(encoding="utf-8")
        parsed = parse_nom_html(html, meta)

        if not parsed:
            log.warning(f"  Failed to parse {nom_id}")
            fail += 1
            continue

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)

        log.info(f"  {nom_id} — {parsed['num_sections']} sections, {parsed['char_count']:,} chars")
        success += 1

    log.info(f"\n=== Parsing complete ===")
    log.info(f"  Parsed:  {success}")
    log.info(f"  Skipped: {skip} (cached)")
    log.info(f"  Failed:  {fail}")


if __name__ == "__main__":
    main()
