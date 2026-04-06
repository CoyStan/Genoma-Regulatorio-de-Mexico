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
from difflib import SequenceMatcher
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.lookup import resolve_law_name, CANONICAL_LAWS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CITATIONS_DIR = Path(__file__).parent.parent / "data" / "citations"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
LOOKUP_DIR = Path(__file__).parent.parent / "data" / "lookup"
LOOKUP_DIR.mkdir(parents=True, exist_ok=True)

FUZZY_THRESHOLD = 0.75

# ---------------------------------------------------------------------------
# Explicit aliases for abrogated/renamed laws and short names
# Maps raw citation name (lowercase) → corpus law_id
# ---------------------------------------------------------------------------

MANUAL_ALIASES: dict[str, str] = {
    # Abrogada en 2023, sucedida por Ley de Humanidades
    "ley de ciencia y tecnología": "ley-general-en-materia-de-humanidades-ciencias-tecnologias-e-innovacion",
    # Nombre corto
    "ley de cámaras empresariales": "ley-de-camaras-empresariales-y-sus-confederaciones",
    # Nombre anterior de la ley de geotermia
    "ley de energía geotérmica": "ley-de-geotermia",
    # Ley abrogada, sucedida por la ley vigente de seguridad pública
    "ley general que establece las bases de coordinación del sistema nacional de seguridad pública": "ley-general-del-sistema-nacional-de-seguridad-publica",
    # Nombre del congreso
    "ley del congreso": "ley-organica-del-congreso-general-de-los-estados-unidos-mexicanos",
    "ley orgánica del congreso": "ley-organica-del-congreso-general-de-los-estados-unidos-mexicanos",
}

# Suffixes to strip before resolving (boilerplate captured by regex)
import re as _re
_TRAILING_JUNK = _re.compile(
    r"\s+(?:para quedar como sigue|y dem[aá]s ordenamientos|y dem[aá]s leyes|"
    r"y dem[aá]s disposiciones|en su art[ií]culo\s+\w+|con anterioridad a|"
    r"del a[ñn]o de que se trate|por el plazo que corresponda|"
    r"y otras leyes|y otras disposiciones|y los dem[aá]s|"
    r"y la ley\s+\w|y de la ley\s+\w|y la presente ley|"
    r"siguientes|contenidas en dicho decreto|o de justicia alternativa respectiva).*$",
    _re.IGNORECASE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Corpus registry — built at startup from data/processed/
# ---------------------------------------------------------------------------

_corpus_aliases: dict[str, str] = {}  # name_lower -> law_id


def build_corpus_registry() -> None:
    """
    Build a reverse-lookup from all processed law files.
    Covers all 318 laws, not just the 48 hardcoded in lookup.py.
    """
    for path in PROCESSED_DIR.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                meta = json.load(f)
            law_id = meta.get("id") or path.stem
            name = meta.get("name", "").strip()
            short = meta.get("short_name", "").strip()
            if name:
                _corpus_aliases[name.lower()] = law_id
            if short:
                _corpus_aliases[short.lower()] = law_id
        except Exception:
            pass


def resolve_from_corpus(raw_name: str) -> dict:
    """Fuzzy-match raw_name against the full corpus registry."""
    cleaned = raw_name.strip().lower()

    # Exact match first
    if cleaned in _corpus_aliases:
        return {
            "law_id": _corpus_aliases[cleaned],
            "confidence": "high",
            "matched_alias": cleaned,
            "score": 1.0,
            "resolution_method": "exact_corpus",
        }

    # Fuzzy match
    best_score = 0.0
    best_id = None
    best_alias = None
    for alias, law_id in _corpus_aliases.items():
        score = SequenceMatcher(None, cleaned, alias).ratio()
        if score > best_score:
            best_score = score
            best_id = law_id
            best_alias = alias

    if best_score >= FUZZY_THRESHOLD:
        confidence = "high" if best_score >= 0.90 else "medium"
        return {
            "law_id": best_id,
            "confidence": confidence,
            "matched_alias": best_alias,
            "score": best_score,
            "resolution_method": "fuzzy_corpus",
        }

    return {
        "law_id": None,
        "confidence": "unresolved",
        "matched_alias": None,
        "score": best_score,
        "resolution_method": "unresolved",
    }


# ---------------------------------------------------------------------------
# Resolution with caching
# ---------------------------------------------------------------------------

_resolution_cache: dict[str, dict] = {}


def _clean_raw_name(raw_name: str) -> str:
    """Strip trailing boilerplate and compound conjunctions captured by regex."""
    return _TRAILING_JUNK.sub("", raw_name).strip()


def resolve_cached(raw_name: str) -> dict:
    """
    Resolve with memoization.
    Order: manual aliases → lookup.py → corpus registry (with cleaned name).
    """
    if raw_name not in _resolution_cache:
        # 1. Manual aliases (abrogated/renamed laws)
        lower = raw_name.strip().lower()
        if lower in MANUAL_ALIASES:
            result = {
                "law_id": MANUAL_ALIASES[lower],
                "confidence": "high",
                "matched_alias": lower,
                "score": 1.0,
                "resolution_method": "manual_override",
            }
        else:
            # 2. lookup.py (48 hardcoded laws)
            result = resolve_law_name(raw_name)
            # Make strategy explicit for observability.
            if result.get("law_id"):
                if result.get("score") == 1.0 and result.get("matched_alias", "").lower() == lower:
                    method = "exact_alias"
                elif result.get("score") == 1.0 and len(result.get("matched_alias", "")) <= 12:
                    method = "acronym_alias"
                elif result.get("score", 0) >= 0.75:
                    method = "fuzzy_alias"
                else:
                    method = "partial_alias"
            else:
                method = "unresolved"
            result["resolution_method"] = method
            # Fall through to corpus when lookup.py is low-confidence OR medium-confidence.
            # Medium fuzzy matches in lookup.py (48 laws) can be wrong — e.g.
            # "Ley General de Desarrollo Social" fuzzy-matches LGSM because they
            # share the "ley general de " prefix. The full corpus (318 laws) is
            # more precise and should take precedence when it finds a better match.
            if not result["law_id"] or result["confidence"] in ("low", "medium"):
                # 3. Corpus registry with cleaned name
                cleaned = _clean_raw_name(raw_name)
                corpus_result = resolve_from_corpus(cleaned)
                if not corpus_result["law_id"] and cleaned != raw_name:
                    corpus_result = resolve_from_corpus(raw_name)
                if corpus_result["law_id"] and corpus_result["score"] >= (result.get("score") or 0):
                    result = corpus_result
        _resolution_cache[raw_name] = result
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
        citation["resolution_method"] = result.get("resolution_method", "unresolved")

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
    method_dist = Counter(c.get("resolution_method", "unresolved") for c in all_citations)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_citations": total,
        "resolved": len(resolved),
        "unresolved": len(unresolved),
        "resolution_rate": round(len(resolved) / total, 4) if total > 0 else 0,
        "by_confidence": dict(confidence_dist),
        "by_resolution_method": dict(method_dist),
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

    build_corpus_registry()
    log.info(f"Corpus registry built: {len(_corpus_aliases)} name entries from {PROCESSED_DIR}")

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
