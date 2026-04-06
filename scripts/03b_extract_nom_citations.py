#!/usr/bin/env python3
"""
03b_extract_nom_citations.py — Extract references from laws to NOMs.

Reads: data/processed/<law_id>.json      (law articles)
       data/processed_noms/_nom_index.json (NOM registry for resolution)

Writes: data/nom_citations/<law_id>_nom_citations.json
        data/nom_citations/_summary.json
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROCESSED_DIR     = Path(__file__).parent.parent / "data" / "processed"
PROCESSED_NOM_DIR = Path(__file__).parent.parent / "data" / "processed_noms"
NOM_CITATIONS_DIR = Path(__file__).parent.parent / "data" / "nom_citations"
NOM_CITATIONS_DIR.mkdir(parents=True, exist_ok=True)

CONTEXT_CHARS = 200

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ── NOM citation patterns ─────────────────────────────────────────────────────
# Matches explicit NOM codes: NOM-043-SSA2-2012, NOM-001-STPS-2008, etc.
NOM_CODE_RE = re.compile(
    r"\b(NOM-\d+[\w]*-[\w\d]+-\d{4})\b",
    re.IGNORECASE,
)

# Matches generic NOM references (captured for counting but not resolved to specific NOM)
NOM_GENERIC_RE = re.compile(
    r"\b(?:Normas?\s+Oficiales?\s+Mexicanas?|NOM\s+(?:aplicable|vigente|correspondiente|respectiva))\b",
    re.IGNORECASE,
)


# ── NOM registry ──────────────────────────────────────────────────────────────

def build_nom_registry() -> dict[str, str]:
    """Build a mapping from NOM code variants to nom_id."""
    registry: dict[str, str] = {}
    for path in PROCESSED_NOM_DIR.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                nom = json.load(f)
            nom_code = nom.get("nom_code", "").upper()
            nom_id   = nom.get("id", path.stem)
            if nom_code:
                registry[nom_code] = nom_id
                # Also register without year: NOM-043-SSA2
                parts = nom_code.split("-")
                if len(parts) >= 3:
                    short = "-".join(parts[:-1])
                    registry.setdefault(short, nom_id)
        except Exception:
            pass
    return registry


# ── Extraction ────────────────────────────────────────────────────────────────

def extract_nom_citations_from_article(
    article: dict,
    source_law_id: str,
    nom_registry: dict[str, str],
) -> list[dict]:
    text    = article.get("text", "")
    art_num = article.get("number", "")
    results = []

    # Explicit NOM code matches
    for m in NOM_CODE_RE.finditer(text):
        raw_code = m.group(1).upper()
        nom_id   = nom_registry.get(raw_code)
        # Try without year if not found
        if not nom_id:
            parts = raw_code.split("-")
            short = "-".join(parts[:-1]) if len(parts) >= 3 else raw_code
            nom_id = nom_registry.get(short)

        start   = max(0, m.start() - CONTEXT_CHARS)
        end     = min(len(text), m.end() + CONTEXT_CHARS)
        context = text[start:end].replace("\n", " ")

        results.append({
            "source_law":      source_law_id,
            "source_article":  art_num,
            "target_nom_raw":  raw_code,
            "target_nom_id":   nom_id or "unresolved",
            "citation_text":   context,
            "pattern_name":    "explicit_nom_code",
            "confidence":      "high" if nom_id else "medium",
            "char_offset":     m.start(),
        })

    # Generic NOM references (counted but not resolved)
    for m in NOM_GENERIC_RE.finditer(text):
        start   = max(0, m.start() - CONTEXT_CHARS)
        end     = min(len(text), m.end() + CONTEXT_CHARS)
        context = text[start:end].replace("\n", " ")

        results.append({
            "source_law":      source_law_id,
            "source_article":  art_num,
            "target_nom_raw":  m.group(0),
            "target_nom_id":   "generic",
            "citation_text":   context,
            "pattern_name":    "generic_nom_reference",
            "confidence":      "low",
            "char_offset":     m.start(),
        })

    return results


def extract_law_nom_citations(law_path: Path, nom_registry: dict) -> list[dict] | None:
    try:
        with open(law_path, encoding="utf-8") as f:
            law = json.load(f)
    except Exception as e:
        log.error(f"Cannot read {law_path}: {e}")
        return None

    law_id   = law.get("id", law_path.stem)
    articles = law.get("articles", [])
    if not articles:
        articles = [{"number": "0", "text": law.get("full_text", "")}]

    all_citations = []
    for article in articles:
        all_citations.extend(
            extract_nom_citations_from_article(article, law_id, nom_registry)
        )

    return all_citations


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=== 03b_extract_nom_citations.py — Genoma Regulatorio de México ===")

    nom_registry = build_nom_registry()
    log.info(f"NOM registry: {len(nom_registry)} entries")

    law_files = sorted(PROCESSED_DIR.glob("*.json"))
    log.info(f"Processing {len(law_files)} laws")

    all_citations_combined = []
    success = fail = 0

    for i, path in enumerate(law_files, 1):
        law_id = path.stem
        out_path = NOM_CITATIONS_DIR / f"{law_id}_nom_citations.json"

        log.info(f"[{i}/{len(law_files)}] {law_id}")
        citations = extract_law_nom_citations(path, nom_registry)

        if citations is None:
            fail += 1
            continue

        explicit = [c for c in citations if c["pattern_name"] == "explicit_nom_code"]
        if explicit:
            log.info(f"  → {len(explicit)} explicit NOM citations")

        output = {
            "law_id":            law_id,
            "extracted_at":      datetime.now(timezone.utc).isoformat(),
            "total_nom_citations": len(citations),
            "citations":         citations,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        all_citations_combined.extend(citations)
        success += 1

    # Summary
    from collections import Counter
    explicit_cits = [c for c in all_citations_combined if c["pattern_name"] == "explicit_nom_code"]
    resolved = [c for c in explicit_cits if c["target_nom_id"] != "unresolved"]
    top_noms = Counter(c["target_nom_id"] for c in resolved).most_common(20)

    summary = {
        "generated_at":       datetime.now(timezone.utc).isoformat(),
        "total_explicit_citations": len(explicit_cits),
        "resolved":           len(resolved),
        "unresolved":         len(explicit_cits) - len(resolved),
        "top_cited_noms":     [{"nom_id": k, "count": v} for k, v in top_noms],
    }
    summary_path = NOM_CITATIONS_DIR / "_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    log.info(f"\n=== Extraction complete ===")
    log.info(f"  Laws processed: {success}")
    log.info(f"  Failed: {fail}")
    log.info(f"  Explicit NOM citations: {len(explicit_cits)}")
    log.info(f"  Resolved: {len(resolved)}")
    log.info(f"  Summary: {summary_path}")


if __name__ == "__main__":
    main()
