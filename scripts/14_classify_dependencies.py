#!/usr/bin/env python3
"""14_classify_dependencies.py

Classifies resolved citations into legal dependency types for lawyer-facing analysis.

Reads:
  data/citations/*_citations.json

Writes:
  data/dependencies/dependencies.json
  data/dependencies/dependency_review_sample.csv
  data/dependencies/dependency_type_summary.json
"""

from __future__ import annotations

import sys
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.dependency_taxonomy import classify_dependency

ROOT = Path(__file__).resolve().parent.parent
CITATIONS_DIR = ROOT / "data" / "citations"
OUT_DIR = ROOT / "data" / "dependencies"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_citations() -> list[dict]:
    all_citations: list[dict] = []
    for path in sorted(CITATIONS_DIR.glob("*_citations.json")):
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        for c in payload.get("citations", []):
            if c.get("target_law_id") and c.get("target_law_id") != "unresolved":
                all_citations.append(c)
    return all_citations


def main() -> None:
    citations = load_citations()
    enriched = []
    dep_type_counter = Counter()

    for c in citations:
        cls = classify_dependency(c)
        dep_type_counter[cls["dependency_type"]] += 1

        enriched.append({
            **c,
            **cls,
            "entity_resolution_method": c.get("resolution_method", "unknown"),
        })

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_dependencies": len(enriched),
        "taxonomy_version": "v1_heuristic",
        "dependencies": enriched,
    }

    with open(OUT_DIR / "dependencies.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    with open(OUT_DIR / "dependency_type_summary.json", "w", encoding="utf-8") as f:
        json.dump({"by_dependency_type": dict(dep_type_counter)}, f, ensure_ascii=False, indent=2)

    sample = enriched[:500]
    with open(OUT_DIR / "dependency_review_sample.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source_law",
                "source_article",
                "target_law_id",
                "target_article",
                "dependency_type",
                "dependency_subtype",
                "dependency_strength",
                "confidence",
                "resolution_method",
                "entity_resolution_method",
                "pattern_name",
                "citation_text",
            ],
        )
        writer.writeheader()
        for row in sample:
            writer.writerow({k: row.get(k) for k in writer.fieldnames})

    print(f"Saved {len(enriched)} classified dependencies to {OUT_DIR / 'dependencies.json'}")


if __name__ == "__main__":
    main()
