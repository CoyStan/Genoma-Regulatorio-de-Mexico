#!/usr/bin/env python3
"""18_reference_fragility.py

Generates fragile/obsolete reference review targets for legal QA workflows.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CITATIONS_DIR = ROOT / "data" / "citations"
DEP_PATH = ROOT / "data" / "dependencies" / "dependencies.json"
OUT_PATH = ROOT / "data" / "dependencies" / "reference_fragility_report.json"


def load_all_citations() -> list[dict]:
    citations = []
    for path in sorted(CITATIONS_DIR.glob("*_citations.json")):
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        citations.extend(payload.get("citations", []))
    return citations


def main() -> None:
    citations = load_all_citations()
    with open(DEP_PATH, encoding="utf-8") as f:
        deps = json.load(f).get("dependencies", [])

    unresolved = [
        c for c in citations
        if not c.get("target_law_id") or c.get("target_law_id") == "unresolved"
    ]

    low_conf = [
        d for d in deps
        if d.get("confidence") == "low" or d.get("dependency_type") == "generic_unresolved"
    ]

    by_raw = Counter((c.get("target_law_raw") or "").strip() for c in unresolved if c.get("target_law_raw"))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "unresolved_reference_count": len(unresolved),
        "low_confidence_dependency_count": len(low_conf),
        "top_unresolved_raw_references": [
            {"raw_reference": name, "count": count}
            for name, count in by_raw.most_common(150)
        ],
        "sample_low_confidence_dependencies": low_conf[:300],
        "notes": [
            "Priorizar revisión manual de referencias no resueltas en reformas de alto impacto.",
            "Corregir alias en lookup y manual overrides puede mejorar sustancialmente cobertura.",
        ],
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Saved reference fragility report to {OUT_PATH}")


if __name__ == "__main__":
    main()
