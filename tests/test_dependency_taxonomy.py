
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.dependency_taxonomy import classify_dependency


def test_definitional_classification():
    c = {
        "citation_text": "Para efectos de esta Ley, se entenderá por trabajador lo dispuesto en la Ley Federal del Trabajo",
        "target_law_raw": "Ley Federal del Trabajo",
        "pattern_name": "direct_mention",
    }
    out = classify_dependency(c)
    assert out["dependency_type"] == "definitional"


def test_supletory_classification():
    c = {
        "citation_text": "En lo no previsto, se aplicará supletoriamente el Código Federal de Procedimientos Civiles",
        "target_law_raw": "Código Federal de Procedimientos Civiles",
        "pattern_name": "conforme_dispuesto",
    }
    out = classify_dependency(c)
    assert out["dependency_type"] == "supletory"


def test_fallback_classification():
    c = {
        "citation_text": "de conformidad con la ley aplicable",
        "target_law_raw": "Ley X",
        "pattern_name": "direct_mention",
    }
    out = classify_dependency(c)
    assert out["dependency_type"] == "generic_unresolved"
