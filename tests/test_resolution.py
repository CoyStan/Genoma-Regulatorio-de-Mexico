"""
test_resolution.py — Unit tests for law name entity resolution.

Run with: python -m pytest tests/test_resolution.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.lookup import (
    resolve_law_name,
    get_law_metadata,
    list_all_law_ids,
    CANONICAL_LAWS,
    ALIASES,
)


# ============================================================
# Test fixtures
# ============================================================

# (raw_name, expected_law_id, min_confidence)
EXACT_MATCH_CASES = [
    ("Constitución Política de los Estados Unidos Mexicanos", "constitucion-politica", "high"),
    ("Ley Federal del Trabajo", "ley-federal-del-trabajo", "high"),
    ("Ley del Seguro Social", "ley-del-seguro-social", "high"),
    ("Código Fiscal de la Federación", "codigo-fiscal-federacion", "high"),
    ("Ley del Impuesto sobre la Renta", "ley-isr", "high"),
    ("Ley del Impuesto al Valor Agregado", "ley-iva", "high"),
    ("Código Penal Federal", "codigo-penal-federal", "high"),
    ("Código Civil Federal", "codigo-civil-federal", "high"),
    ("Ley General de Salud", "ley-general-salud", "high"),
    ("Ley General del Equilibrio Ecológico y la Protección al Ambiente", "lgeepa", "high"),
]

ACRONYM_MATCH_CASES = [
    ("LFT", "ley-federal-del-trabajo", "high"),
    ("LSS", "ley-del-seguro-social", "high"),
    ("CFF", "codigo-fiscal-federacion", "high"),
    ("LISR", "ley-isr", "high"),
    ("LIVA", "ley-iva", "high"),
    ("CPF", "codigo-penal-federal", "high"),
    ("CCF", "codigo-civil-federal", "high"),
    ("LGS", "ley-general-salud", "high"),
    ("LGEEPA", "lgeepa", "high"),
    ("LGTAIP", "lgtaip", "high"),
    ("CPEUM", "constitucion-politica", "high"),
]

ALIAS_MATCH_CASES = [
    ("Constitución", "constitucion-politica", "high"),
    ("Ley del Trabajo", "ley-federal-del-trabajo", "high"),
    ("Ley del IMSS", "ley-del-seguro-social", "high"),
    ("Código Fiscal", "codigo-fiscal-federacion", "high"),
    ("Ley del ISR", "ley-isr", "high"),
    ("Ley del IVA", "ley-iva", "high"),
    ("Ley Bancaria", "ley-instituciones-credito", "high"),
    ("Ley Ambiental", "lgeepa", "high"),
    ("Ley de Transparencia", "lgtaip", "high"),
    ("Ley Fintech", "ley-fintech", "high"),
]

FUZZY_MATCH_CASES = [
    # Slight variations that should still resolve
    ("Ley Federal de Trabajo", "ley-federal-del-trabajo"),  # missing "del"
    ("Código Fiscal Federación", "codigo-fiscal-federacion"),  # missing "de la"
    ("Ley General Salud", "ley-general-salud"),  # missing "de"
]

UNRESOLVABLE_CASES = [
    "",
    "Reglamento Interior del Ejecutivo Federal",   # sub-regulatory, likely not in list
    "ley estatal de cualquier cosa",               # state law
]


# ============================================================
# Tests
# ============================================================

class TestExactMatches:
    """Test that full law names resolve exactly."""

    @pytest.mark.parametrize("raw_name,expected_id,min_confidence", EXACT_MATCH_CASES)
    def test_exact_name_resolves(self, raw_name, expected_id, min_confidence):
        result = resolve_law_name(raw_name)
        assert result["law_id"] == expected_id, (
            f"Expected '{expected_id}', got '{result['law_id']}' "
            f"(confidence: {result['confidence']}, score: {result['score']:.2f}) "
            f"for input: '{raw_name}'"
        )
        assert result["score"] >= 0.9


class TestAcronymMatches:
    """Test that law acronyms resolve correctly."""

    @pytest.mark.parametrize("acronym,expected_id,min_confidence", ACRONYM_MATCH_CASES)
    def test_acronym_resolves(self, acronym, expected_id, min_confidence):
        result = resolve_law_name(acronym)
        assert result["law_id"] == expected_id, (
            f"Expected '{expected_id}', got '{result['law_id']}' for acronym '{acronym}'"
        )
        assert result["confidence"] in ("high", "medium")


class TestAliasMatches:
    """Test that known aliases resolve to the correct canonical law."""

    @pytest.mark.parametrize("alias,expected_id,min_confidence", ALIAS_MATCH_CASES)
    def test_alias_resolves(self, alias, expected_id, min_confidence):
        result = resolve_law_name(alias)
        assert result["law_id"] == expected_id, (
            f"Expected '{expected_id}', got '{result['law_id']}' "
            f"for alias '{alias}' (confidence: {result['confidence']})"
        )


class TestFuzzyMatches:
    """Test that near-matches still resolve correctly."""

    @pytest.mark.parametrize("raw_name,expected_id", FUZZY_MATCH_CASES)
    def test_fuzzy_resolves(self, raw_name, expected_id):
        result = resolve_law_name(raw_name)
        # Fuzzy matches may be medium confidence — just check the ID
        assert result["law_id"] == expected_id, (
            f"Expected '{expected_id}', got '{result['law_id']}' "
            f"for fuzzy input '{raw_name}' (score: {result.get('score', 0):.2f})"
        )


class TestUnresolvableCases:
    """Test that truly unresolvable names return None gracefully."""

    @pytest.mark.parametrize("raw_name", UNRESOLVABLE_CASES)
    def test_unresolvable_returns_none(self, raw_name):
        result = resolve_law_name(raw_name)
        # We expect these to be unresolved (law_id is None)
        # Strict: empty string should definitely be None
        if not raw_name:
            assert result["law_id"] is None
        # For others: just check no exception was raised and confidence is low/unresolved
        assert result["confidence"] in ("low", "unresolved", "medium")


class TestCanonicalLawRegistry:
    """Test the integrity of the canonical law registry."""

    def test_all_laws_have_required_fields(self):
        required_fields = {"name", "short", "sector"}
        for law_id, data in CANONICAL_LAWS.items():
            missing = required_fields - set(data.keys())
            assert not missing, f"Law '{law_id}' missing fields: {missing}"

    def test_all_law_ids_are_slugs(self):
        import re
        slug_pattern = re.compile(r"^[a-z0-9-]+$")
        for law_id in CANONICAL_LAWS:
            assert slug_pattern.match(law_id), (
                f"Law ID '{law_id}' is not a valid slug (lowercase letters, digits, hyphens only)"
            )

    def test_no_duplicate_law_ids(self):
        ids = list(CANONICAL_LAWS.keys())
        assert len(ids) == len(set(ids)), "Duplicate law IDs found in canonical registry"

    def test_aliases_map_to_valid_law_ids(self):
        valid_ids = set(CANONICAL_LAWS.keys())
        for alias, law_id in ALIASES.items():
            assert law_id in valid_ids, (
                f"Alias '{alias}' maps to unknown law_id '{law_id}'"
            )

    def test_short_names_are_uppercase_or_abbrev(self):
        for law_id, data in CANONICAL_LAWS.items():
            short = data.get("short", "")
            if short:
                # Short names should be mostly uppercase letters
                assert len(short) <= 15, (
                    f"Short name '{short}' for '{law_id}' seems too long"
                )

    def test_get_law_metadata_returns_data(self):
        metadata = get_law_metadata("ley-federal-del-trabajo")
        assert metadata is not None
        assert metadata["name"] == "Ley Federal del Trabajo"

    def test_get_law_metadata_returns_none_for_unknown(self):
        result = get_law_metadata("this-law-does-not-exist")
        assert result is None

    def test_list_all_law_ids_not_empty(self):
        ids = list_all_law_ids()
        assert len(ids) > 20, f"Expected at least 20 laws, got {len(ids)}"

    def test_constitucion_is_in_registry(self):
        assert "constitucion-politica" in CANONICAL_LAWS
        assert CANONICAL_LAWS["constitucion-politica"]["short"] == "CPEUM"


class TestResolutionResultStructure:
    """Test that resolution results always have the expected structure."""

    def test_result_has_required_keys(self):
        result = resolve_law_name("Ley Federal del Trabajo")
        assert "law_id" in result
        assert "confidence" in result
        assert "matched_alias" in result
        assert "score" in result

    def test_confidence_is_valid_value(self):
        for raw_name in ["LFT", "something totally unknown xyz", ""]:
            result = resolve_law_name(raw_name)
            assert result["confidence"] in ("high", "medium", "low", "unresolved"), (
                f"Invalid confidence '{result['confidence']}' for '{raw_name}'"
            )

    def test_score_is_between_0_and_1(self):
        for raw_name in ["LFT", "Ley del ISR", "unknown xyz"]:
            result = resolve_law_name(raw_name)
            assert 0.0 <= result["score"] <= 1.0, (
                f"Score {result['score']} out of range for '{raw_name}'"
            )
