#!/usr/bin/env python3
"""19_validate_dependency_outputs.py

Lightweight validation hooks for dependency classification and entity resolution auditability.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEP_PATH = ROOT / "data" / "dependencies" / "dependencies.json"
LOOKUP_PATH = ROOT / "data" / "lookup" / "resolution_log.json"

REQUIRED_DEP_FIELDS = {
    "dependency_type",
    "dependency_subtype",
    "dependency_strength",
    "resolution_method",
    "explanation",
    "confidence",
    "entity_resolution_method",
}


def main() -> None:
    errors = []

    if not DEP_PATH.exists():
        raise SystemExit(f"Missing dependency dataset: {DEP_PATH}")
    if not LOOKUP_PATH.exists():
        raise SystemExit(f"Missing resolution log: {LOOKUP_PATH}")

    with open(DEP_PATH, encoding="utf-8") as f:
        deps = json.load(f).get("dependencies", [])
    with open(LOOKUP_PATH, encoding="utf-8") as f:
        lookup = json.load(f)

    for idx, dep in enumerate(deps[:5000]):
        missing = REQUIRED_DEP_FIELDS - set(dep.keys())
        if missing:
            errors.append(f"Dependency row {idx} missing fields: {sorted(missing)}")

    if "by_resolution_method" not in lookup:
        errors.append("resolution_log.json missing 'by_resolution_method'")

    if errors:
        print("Validation failed:")
        for e in errors[:40]:
            print(f"- {e}")
        raise SystemExit(1)

    print("Validation passed: dependency outputs and resolution observability look consistent.")


if __name__ == "__main__":
    main()
