#!/usr/bin/env python3
"""
03_extract_citations.py — Extract cross-references (citations) from all laws.

Reads: data/processed/<law_id>.json
Writes: data/citations/<law_id>_citations.json

Each citation record contains:
    {
        "source_law": "ley-federal-del-trabajo",
        "source_article": "123",
        "target_law_raw": "Ley del Seguro Social",  # as written in text
        "target_law_id": null,                        # resolved in step 04
        "target_article": "5",                        # if specified
        "citation_text": "...conforme a lo dispuesto en la Ley del Seguro Social...",
        "pattern_name": "conforme_dispuesto",
        "confidence": "high",
        "char_offset": 12453,
    }
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.patterns import (
    PRIMARY_PATTERNS,
    SECONDARY_PATTERNS,
    CONSTITUTIONAL_PATTERNS,
    ARTICLE_PATTERN,
    clean_law_name,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
CITATIONS_DIR = Path(__file__).parent.parent / "data" / "citations"
CITATIONS_DIR.mkdir(parents=True, exist_ok=True)

CONTEXT_CHARS = 150  # Characters of context to capture around each match

# ---------------------------------------------------------------------------
# False-positive suppression for direct_mention
# ---------------------------------------------------------------------------

_DEROGATION_CTX = re.compile(
    r"\b(?:se\s+derogan?|quedan?\s+(?:abrogad|derogad)|se\s+abroga)\b",
    re.IGNORECASE,
)
_AMENDMENT_CTX = re.compile(
    r"\bDECRETO\s+por\s+el\s+que\s+se\s+(?:reform|adic)",
    re.IGNORECASE,
)
# Enumeration lists: "de la Ley X, de la Ley Y" or "I. La Ley X; II. La Ley Y"
# These appear in definitional articles and transitories that enumerate governing laws.
_LIST_CTX = re.compile(
    r"(?:"
    r"(?:de\s+la\s+Ley|del\s+(?:Código|Reglamento))[^;,\n]{5,80}[,;]\s*(?:de\s+la\s+Ley|del\s+(?:Código|Reglamento))"
    r"|"
    r"[IVX]+\.\s+(?:La\s+)?(?:Ley|Código)[^;\n]{5,80};\s*[IVX]+\.\s+(?:La\s+)?(?:Ley|Código)"
    r")",
    re.IGNORECASE,
)
_GENERIC_RAW = re.compile(
    r"(?:de\s+la\s+materia"
    r"|de\s+esta\s+[Ll]ey"
    r"|de\s+la\s+presente\s+[Ll]ey"
    r"|[Rr]eglamento\s+de\s+esta"
    r"|[Rr]eglamento\s+de\s+la\s+presente)",
    re.IGNORECASE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Citation extraction
# ---------------------------------------------------------------------------

def _is_direct_mention_false_positive(raw_name: str, context: str) -> bool:
    if _DEROGATION_CTX.search(context):
        return True
    if _AMENDMENT_CTX.search(context):
        return True
    if _LIST_CTX.search(context):
        return True
    if _GENERIC_RAW.search(raw_name):
        return True
    return False


def extract_citations_from_article(
    article: dict,
    source_law_id: str,
) -> list[dict]:
    """
    Extract all citations from a single article.
    Returns a list of citation dicts.
    """
    text = article.get("text", "")
    article_number = article.get("number", "")
    citations = []

    # Run all pattern groups
    all_pattern_groups = [
        ("primary", PRIMARY_PATTERNS),
        ("secondary", SECONDARY_PATTERNS),
    ]

    for group_name, patterns in all_pattern_groups:
        for pat_info in patterns:
            pattern = pat_info["pattern"]
            for match in pattern.finditer(text):
                raw_name = match.group(1) if match.lastindex and match.group(1) else ""
                raw_name = clean_law_name(raw_name)

                if not raw_name or len(raw_name) < 5:
                    continue

                # Extract surrounding context
                start = max(0, match.start() - CONTEXT_CHARS)
                end = min(len(text), match.end() + CONTEXT_CHARS)
                context = text[start:end].replace("\n", " ")

                # Suppress false positives for direct_mention only
                if pat_info["name"] == "direct_mention":
                    if _is_direct_mention_false_positive(raw_name, context):
                        continue

                # Try to find target article number in the match text
                target_article = None
                art_match = ARTICLE_PATTERN.search(match.group(0))
                if art_match:
                    target_article = art_match.group(1)

                citations.append({
                    "source_law": source_law_id,
                    "source_article": article_number,
                    "target_law_raw": raw_name,
                    "target_law_id": None,  # resolved in step 04
                    "target_article": target_article,
                    "citation_text": context,
                    "pattern_name": pat_info["name"],
                    "pattern_group": group_name,
                    "confidence": pat_info["confidence"],
                    "char_offset": match.start(),
                })

    # Constitutional references (special handling)
    for pat_info in CONSTITUTIONAL_PATTERNS:
        pattern = pat_info["pattern"]
        for match in pattern.finditer(text):
            # For constitutional refs, group 1 is the article number (not the law name)
            article_ref = match.group(1).strip() if match.lastindex and match.group(1) else ""

            start = max(0, match.start() - CONTEXT_CHARS)
            end = min(len(text), match.end() + CONTEXT_CHARS)
            context = text[start:end].replace("\n", " ")

            citations.append({
                "source_law": source_law_id,
                "source_article": article_number,
                "target_law_raw": "Constitución Política de los Estados Unidos Mexicanos",
                "target_law_id": "constitucion-politica-de-los-estados-unidos-mexicanos",  # always resolved
                "target_article": article_ref,
                "citation_text": context,
                "pattern_name": pat_info["name"],
                "pattern_group": "constitutional",
                "confidence": pat_info["confidence"],
                "char_offset": match.start(),
            })

    return citations


def deduplicate_citations(citations: list[dict]) -> list[dict]:
    """
    Remove duplicate citations (same source article + target law + pattern).
    Keep the highest-confidence version.
    """
    seen: dict[tuple, dict] = {}
    confidence_rank = {"high": 3, "medium": 2, "low": 1}

    for citation in citations:
        key = (
            citation["source_law"],
            citation["source_article"],
            citation["target_law_raw"].lower()[:50],
        )
        existing = seen.get(key)
        if existing is None:
            seen[key] = citation
        else:
            # Keep higher confidence
            if confidence_rank.get(citation["confidence"], 0) > confidence_rank.get(existing["confidence"], 0):
                seen[key] = citation

    return list(seen.values())


def extract_law_citations(processed_path: Path) -> list[dict] | None:
    """
    Extract all citations from a processed law file.
    Returns list of citation dicts or None if processing failed.
    """
    try:
        with open(processed_path, encoding="utf-8") as f:
            law = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.error(f"Cannot read {processed_path}: {e}")
        return None

    law_id = law.get("id", processed_path.stem)
    articles = law.get("articles", [])

    if not articles:
        # Fall back to extracting from full_text if no articles were parsed
        log.warning(f"No articles in {law_id}, using full_text fallback")
        articles = [{"number": "0", "text": law.get("full_text", "")}]

    all_citations = []
    for article in articles:
        article_citations = extract_citations_from_article(article, law_id)
        all_citations.extend(article_citations)

    # Deduplicate
    all_citations = deduplicate_citations(all_citations)

    # Filter self-references (a law citing itself — valid but less interesting)
    external = [c for c in all_citations if c["target_law_raw"].lower() not in [
        law.get("name", "").lower(),
        law.get("short_name", "").lower(),
    ]]
    self_refs = len(all_citations) - len(external)

    log.info(f"  → {len(external)} citations ({self_refs} self-references filtered)")
    return external


def already_extracted(law_id: str) -> bool:
    """Return True if citations have already been extracted for this law."""
    return (CITATIONS_DIR / f"{law_id}_citations.json").exists()


def save_citations(law_id: str, citations: list[dict]) -> None:
    output_path = CITATIONS_DIR / f"{law_id}_citations.json"
    output = {
        "law_id": law_id,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "total_citations": len(citations),
        "citations": citations,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    log.info(f"  → Saved: {output_path.name}")


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def compute_citation_summary(all_citations: list[dict]) -> dict:
    """Compute aggregate stats across all citations."""
    from collections import Counter

    pattern_counts = Counter(c["pattern_name"] for c in all_citations)
    confidence_counts = Counter(c["confidence"] for c in all_citations)
    top_targets = Counter(c["target_law_raw"] for c in all_citations).most_common(20)

    return {
        "total_citations": len(all_citations),
        "by_pattern": dict(pattern_counts.most_common()),
        "by_confidence": dict(confidence_counts),
        "top_cited_laws_raw": [{"name": name, "count": count} for name, count in top_targets],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=== 03_extract_citations.py — Genoma Regulatorio de México ===")

    processed_files = sorted(PROCESSED_DIR.glob("*.json"))
    if not processed_files:
        log.error(f"No processed files in {PROCESSED_DIR}. Run 02_parse.py first.")
        sys.exit(1)

    log.info(f"Extracting citations from {len(processed_files)} laws")

    all_citations_combined = []
    success = 0
    fail = 0

    for i, path in enumerate(processed_files, 1):
        law_id = path.stem
        log.info(f"[{i}/{len(processed_files)}] {law_id}")

        citations = extract_law_citations(path)
        if citations is None:
            fail += 1
            continue

        save_citations(law_id, citations)
        all_citations_combined.extend(citations)
        success += 1

    # Save combined summary
    summary = compute_citation_summary(all_citations_combined)
    summary_path = CITATIONS_DIR / "_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    log.info(f"\n=== Extraction complete ===")
    log.info(f"  Laws processed: {success}")
    log.info(f"  Failed: {fail}")
    log.info(f"  Total citations extracted: {len(all_citations_combined)}")
    log.info(f"  Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
