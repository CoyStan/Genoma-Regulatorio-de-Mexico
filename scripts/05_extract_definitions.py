#!/usr/bin/env python3
"""
05_extract_definitions.py — Extract legal definitions from all laws.

Reads: data/processed/<law_id>.json
Writes: data/definitions/<law_id>_definitions.json
        data/definitions/_all_definitions.json (combined)

Each definition record:
    {
        "law_id": "ley-general-salud",
        "law_name": "Ley General de Salud",
        "article": "6",
        "term": "servicio de salud",
        "definition_text": "Para los efectos de esta Ley, se entiende por...",
        "raw_snippet": "...",
    }
"""

import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.patterns import DEFINITION_PATTERNS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
DEFINITIONS_DIR = Path(__file__).parent.parent / "data" / "definitions"
DEFINITIONS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Definition extraction
# ---------------------------------------------------------------------------

# Pattern to match defined terms in definition blocks
# Typically: "I. [term]: definition text"
# or: "[term]: definition text"
DEFINITION_ITEM_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:[IVXivx]+\.|[\d]+\.|[a-z]\))\s+"
    r"([A-Za-záéíóúüñÁÉÍÓÚÜÑ][\w\s,\-]{2,80}?)\s*[:;]\s*"
    r"([\s\S]{10,500}?)(?=(?:\n\s*(?:[IVXivx]+\.|[\d]+\.|[a-z]\))\s)|$)",
    re.MULTILINE,
)

# Simple "se entiende por [term] [definition]" pattern
SE_ENTIENDE_PATTERN = re.compile(
    r"[Ss]e\s+entiende\s+(?:por|como)\s+"
    r"\"?([A-Za-záéíóúüñÁÉÍÓÚÜÑ][\w\s,\-]{2,80}?)\"?"
    r"\s*[,:]?\s*"
    r"([\w][\s\S]{10,300}?)(?=[.;](?:\s*$|\s+[A-Z]))",
    re.MULTILINE,
)

# "se considera [term] a [definition]"
SE_CONSIDERA_PATTERN = re.compile(
    r"[Ss]e\s+considera[rá]*\s+"
    r"\"?([A-Za-záéíóúüñÁÉÍÓÚÜÑ][\w\s,\-]{2,60}?)\"?"
    r"\s+(?:a|como|aquell[ao])\s+"
    r"([\w][\s\S]{10,300}?)(?=[.;](?:\s*$|\s+[A-Z]))",
    re.MULTILINE,
)


def find_definition_blocks(text: str) -> list[dict]:
    """
    Identify text blocks that are definition sections.
    Returns list of {start, end, trigger_pattern}.
    """
    blocks = []
    for pattern in DEFINITION_PATTERNS:
        for match in pattern.finditer(text):
            # Take the next 2000 characters as the potential definition block
            block_start = match.start()
            block_end = min(len(text), match.end() + 2000)
            blocks.append({
                "start": block_start,
                "end": block_end,
                "trigger_text": match.group(0),
                "block_text": text[block_start:block_end],
            })
    return blocks


def extract_definitions_from_article(
    article: dict,
    law_id: str,
    law_name: str,
) -> list[dict]:
    """Extract definitions from a single article."""
    text = article.get("text", "")
    article_number = article.get("number", "")
    definitions = []

    # Check if this article contains a definition section trigger
    has_definition_trigger = any(p.search(text) for p in DEFINITION_PATTERNS)
    if not has_definition_trigger:
        # Also check for inline definitions
        for match in SE_ENTIENDE_PATTERN.finditer(text):
            term = match.group(1).strip()
            def_text = match.group(2).strip()
            if term and def_text and len(term) < 80:
                definitions.append({
                    "law_id": law_id,
                    "law_name": law_name,
                    "article": article_number,
                    "term": term.lower(),
                    "definition_text": def_text,
                    "extraction_method": "se_entiende",
                })
        return definitions

    # Extract from definition blocks
    blocks = find_definition_blocks(text)
    for block in blocks:
        block_text = block["block_text"]

        # Try roman numeral / numbered list items
        for match in DEFINITION_ITEM_PATTERN.finditer(block_text):
            term = match.group(1).strip()
            def_text = match.group(2).strip()
            if term and def_text and 3 <= len(term) <= 80:
                definitions.append({
                    "law_id": law_id,
                    "law_name": law_name,
                    "article": article_number,
                    "term": term.lower(),
                    "definition_text": def_text[:500],  # Truncate for storage
                    "raw_snippet": block["trigger_text"][:100],
                    "extraction_method": "definition_block",
                })

    # Inline "se considera" patterns
    for match in SE_CONSIDERA_PATTERN.finditer(text):
        term = match.group(1).strip()
        def_text = match.group(2).strip()
        if term and def_text and len(term) < 80:
            definitions.append({
                "law_id": law_id,
                "law_name": law_name,
                "article": article_number,
                "term": term.lower(),
                "definition_text": def_text,
                "extraction_method": "se_considera",
            })

    return definitions


def detect_definition_conflicts(all_definitions: list[dict]) -> list[dict]:
    """
    Find cases where the same term is defined differently in multiple laws.
    Returns list of conflict records.
    """
    by_term: dict[str, list[dict]] = defaultdict(list)
    for defn in all_definitions:
        by_term[defn["term"]].append(defn)

    conflicts = []
    for term, definitions in by_term.items():
        if len(definitions) > 1:
            # Check if definitions actually differ (not just whitespace)
            unique_defs = set(
                re.sub(r"\s+", " ", d["definition_text"][:100]).strip().lower()
                for d in definitions
            )
            if len(unique_defs) > 1:
                conflicts.append({
                    "term": term,
                    "num_laws": len(definitions),
                    "laws": [d["law_id"] for d in definitions],
                    "definitions": [
                        {"law_id": d["law_id"], "article": d["article"],
                         "definition": d["definition_text"][:200]}
                        for d in definitions
                    ],
                })

    return sorted(conflicts, key=lambda x: x["num_laws"], reverse=True)


def process_law_definitions(processed_path: Path) -> list[dict] | None:
    """Extract definitions from a processed law file."""
    try:
        with open(processed_path, encoding="utf-8") as f:
            law = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.error(f"Cannot read {processed_path}: {e}")
        return None

    law_id = law.get("id", processed_path.stem)
    law_name = law.get("name", "")
    articles = law.get("articles", [])

    if not articles:
        return []

    all_definitions = []
    for article in articles:
        article_defs = extract_definitions_from_article(article, law_id, law_name)
        all_definitions.extend(article_defs)

    log.info(f"  → {len(all_definitions)} definitions extracted")
    return all_definitions


def save_definitions(law_id: str, definitions: list[dict]) -> None:
    output_path = DEFINITIONS_DIR / f"{law_id}_definitions.json"
    output = {
        "law_id": law_id,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "total_definitions": len(definitions),
        "definitions": definitions,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=== 05_extract_definitions.py — Genoma Regulatorio de México ===")

    processed_files = sorted(PROCESSED_DIR.glob("*.json"))
    if not processed_files:
        log.error(f"No processed files in {PROCESSED_DIR}. Run 02_parse.py first.")
        sys.exit(1)

    log.info(f"Extracting definitions from {len(processed_files)} laws")

    all_definitions = []
    success = 0
    fail = 0

    for i, path in enumerate(processed_files, 1):
        law_id = path.stem
        log.info(f"[{i}/{len(processed_files)}] {law_id}")

        definitions = process_law_definitions(path)
        if definitions is None:
            fail += 1
            continue

        save_definitions(law_id, definitions)
        all_definitions.extend(definitions)
        success += 1

    log.info(f"\nTotal definitions extracted: {len(all_definitions)}")

    # Find conflicts
    log.info("Detecting definition conflicts...")
    conflicts = detect_definition_conflicts(all_definitions)
    log.info(f"Found {len(conflicts)} terms defined differently in multiple laws")

    # Save combined definitions and conflicts
    combined_path = DEFINITIONS_DIR / "_all_definitions.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_definitions": len(all_definitions),
                "total_conflicts": len(conflicts),
                "top_conflicts": conflicts[:50],
                "all_definitions": all_definitions,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    log.info(f"\n=== Definition extraction complete ===")
    log.info(f"  Laws processed: {success}")
    log.info(f"  Failed: {fail}")
    log.info(f"  Total definitions: {len(all_definitions)}")
    log.info(f"  Definition conflicts: {len(conflicts)}")
    log.info(f"  Output: {combined_path}")


if __name__ == "__main__":
    main()
