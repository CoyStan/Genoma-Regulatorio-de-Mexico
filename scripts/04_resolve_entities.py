#!/usr/bin/env python3
"""
04_resolve_entities.py — Resolve raw citation target names to canonical law IDs.

Reads: data/citations/<law_id>_citations.json (from step 03)
Writes: data/citations/<law_id>_citations.json (in-place update)
        data/lookup/resolution_log.json (all resolution decisions)
        data/lookup/unresolved.json (citations that couldn't be matched)

Resolution strategy:
    1. Exact match against alias table
    2. Acronym match
    3. Fuzzy string matching (difflib SequenceMatcher)
    4. Partial match (first N characters)
    5. Flag as unresolved

All resolutions are logged with confidence scores for manual review.
"""

import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.lookup import resolve_law_name, CANONICAL_LAWS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CITATIONS_DIR = Path(__file__).parent.parent / "data" / "citations"
LOOKUP_DIR = Path(__file__).parent.parent / "data" / "lookup"
LOOKUP_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Resolution with caching
# ---------------------------------------------------------------------------

_resolution_cache: dict[str, dict] = {}


def resolve_cached(raw_name: str) -> dict:
    """Resolve with memoization to avoid re-running fuzzy matching."""
    if raw_name not in _resolution_cache:
        _resolution_cache[raw_name] = resolve_law_name(raw_name)
    return _resolution_cache[raw_name]


def resolve_citations_file(citations_path: Path) -> tuple[int, int, int]:
    """
    Resolve all citations in a single citations file.
    Updates target_law_id in-place.
    Returns (resolved_count, already_resolved, unresolved).
    """
    try:
        with open(citations_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.error(f"Cannot read {citations_path}: {e}")
        return 0, 0, 0

    citations = data.get("citations", [])
    resolved = 0
    already = 0
    unresolved = 0

    for citation in citations:
        # Skip if already resolved (e.g., constitutional references set in step 03)
        if citation.get("target_law_id") and citation["target_law_id"] != "unresolved":
            already += 1
            continue

        raw_name = citation.get("target_law_raw", "")
        if not raw_name:
            unresolved += 1
            continue

        result = resolve_cached(raw_name)
        citation["target_law_id"] = result["law_id"]
        citation["resolution_confidence"] = result["confidence"]
        citation["resolution_score"] = result["score"]
        citation["resolution_matched_alias"] = result["matched_alias"]

        if result["law_id"]:
            resolved += 1
        else:
            unresolved += 1
            citation["target_law_id"] = "unresolved"

    # Write back updated citations
    data["resolved_at"] = datetime.now(timezone.utc).isoformat()
    with open(citations_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return resolved, already, unresolved


# ---------------------------------------------------------------------------
# Aggregate resolution analysis
# ---------------------------------------------------------------------------

def build_resolution_report(all_citations: list[dict]) -> dict:
    """Build a comprehensive resolution report across all citations."""
    total = len(all_citations)
    resolved = [c for c in all_citations if c.get("target_law_id") and c["target_law_id"] != "unresolved"]
    unresolved = [c for c in all_citations if not c.get("target_law_id") or c["target_law_id"] == "unresolved"]

    # Count resolutions by target law
    target_counts = Counter(c["target_law_id"] for c in resolved)

    # Unresolved raw names (for manual review)
    unresolved_names = Counter(c.get("target_law_raw", "") for c in unresolved)

    # Resolution confidence distribution
    confidence_dist = Counter(c.get("resolution_confidence", "unresolved") for c in all_citations)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_citations": total,
        "resolved": len(resolved),
        "unresolved": len(unresolved),
        "resolution_rate": round(len(resolved) / total, 4) if total > 0 else 0,
        "by_confidence": dict(confidence_dist),
        "top_cited_laws": [
            {
                "law_id": law_id,
                "name": CANONICAL_LAWS.get(law_id, {}).get("name", law_id),
                "citation_count": count,
            }
            for law_id, count in target_counts.most_common(30)
        ],
        "top_unresolved": [
            {"raw_name": name, "count": count}
            for name, count in unresolved_names.most_common(50)
            if name
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=== 04_resolve_entities.py — Genoma Regulatorio de México ===")

    citation_files = sorted(CITATIONS_DIR.glob("*_citations.json"))
    if not citation_files:
        log.error(f"No citation files in {CITATIONS_DIR}. Run 03_extract_citations.py first.")
        sys.exit(1)

    log.info(f"Resolving entities in {len(citation_files)} citation files")

    total_resolved = 0
    total_already = 0
    total_unresolved = 0
    all_citations = []

    for i, path in enumerate(citation_files, 1):
        log.info(f"[{i}/{len(citation_files)}] {path.name}")
        resolved, already, unresolved = resolve_citations_file(path)
        total_resolved += resolved
        total_already += already
        total_unresolved += unresolved
        log.info(f"  → resolved: {resolved}, already resolved: {already}, unresolved: {unresolved}")

        # Collect all citations for report
        try:
            with open(path) as f:
                data = json.load(f)
            all_citations.extend(data.get("citations", []))
        except Exception:
            pass

    # Build and save resolution report
    report = build_resolution_report(all_citations)
    report_path = LOOKUP_DIR / "resolution_log.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Save unresolved for manual review
    unresolved_list = [
        c for c in all_citations
        if not c.get("target_law_id") or c["target_law_id"] == "unresolved"
    ]
    unresolved_path = LOOKUP_DIR / "unresolved.json"
    with open(unresolved_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "count": len(unresolved_list),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "unresolved_citations": unresolved_list[:500],  # First 500 for review
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    log.info(f"\n=== Resolution complete ===")
    log.info(f"  Newly resolved: {total_resolved}")
    log.info(f"  Already resolved: {total_already}")
    log.info(f"  Unresolved: {total_unresolved}")
    log.info(f"  Resolution rate: {report['resolution_rate']:.1%}")
    log.info(f"  Report: {report_path}")
    log.info(f"  Unresolved for review: {unresolved_path}")


if __name__ == "__main__":
    main()
