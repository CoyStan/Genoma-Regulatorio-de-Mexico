"""
test_patterns.py — Unit tests for citation extraction patterns.

Run with: python -m pytest tests/test_patterns.py -v
"""

import sys
from pathlib import Path

import pytest

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.patterns import (
    PRIMARY_PATTERNS,
    SECONDARY_PATTERNS,
    CONSTITUTIONAL_PATTERNS,
    clean_law_name,
    extract_article_number,
)


# ============================================================
# Test fixtures: real-world-like citation text samples
# ============================================================

# (pattern_name, input_text, expected_match_substring)
PRIMARY_TEST_CASES = [
    (
        "conforme_dispuesto",
        "conforme a lo dispuesto en la Ley Federal del Trabajo, el empleador deberá",
        "Ley Federal del Trabajo",
    ),
    (
        "conforme_dispuesto",
        "conforme a lo dispuesto por el Código Fiscal de la Federación en su artículo 14",
        "Código Fiscal de la Federación",
    ),
    (
        "terminos_establecido",
        "en términos de lo establecido en la Ley del Seguro Social",
        "Ley del Seguro Social",
    ),
    (
        "de_acuerdo",
        "de acuerdo con la Ley General de Salud, los servicios médicos",
        "Ley General de Salud",
    ),
    (
        "lo_previsto",
        "lo previsto en la Ley de Aguas Nacionales para el otorgamiento",
        "Ley de Aguas Nacionales",
    ),
    (
        "conformidad",
        "de conformidad con la Ley Federal de Protección al Consumidor",
        "Ley Federal de Protección al Consumidor",
    ),
    (
        "en_los_terminos",
        "en los términos de la Ley de Instituciones de Crédito",
        "Ley de Instituciones de Crédito",
    ),
    (
        "a_que_refiere",
        "a que se refiere la Ley del Mercado de Valores en el título segundo",
        "Ley del Mercado de Valores",
    ),
    (
        "lo_dispuesto",
        "lo dispuesto por la Ley General del Equilibrio Ecológico y la Protección al Ambiente",
        "Ley General del Equilibrio Ecológico y la Protección al Ambiente",
    ),
    (
        "lo_dispuesto",
        "lo dispuesto en la Ley de Amparo, Reglamentaria de los Artículos 103 y 107",
        "Ley de Amparo",
    ),
    (
        "prevista_en",
        "prevista en la Ley Federal de Telecomunicaciones y Radiodifusión",
        "Ley Federal de Telecomunicaciones y Radiodifusión",
    ),
    (
        "establecida_en",
        "establecida en la Ley General de Transparencia y Acceso a la Información Pública",
        "Ley General de Transparencia",
    ),
    (
        "regulada_por",
        "regulada por la Ley de Migración y sus disposiciones reglamentarias",
        "Ley de Migración",
    ),
    (
        "senalada_en",
        "señalada en la Ley de Seguridad Nacional para los órganos de inteligencia",
        "Ley de Seguridad Nacional",
    ),
]

CONSTITUTIONAL_TEST_CASES = [
    (
        "constitucion_full",
        "conforme al artículo 123 de la Constitución Política de los Estados Unidos Mexicanos",
        "123",
    ),
    (
        "constitucion_full",
        "de conformidad con los artículos 25 y 26 de la Constitución Política de los Estados Unidos Mexicanos",
        "25",
    ),
    (
        "articulo_constitucional",
        "el artículo 27 constitucional establece el dominio de la nación",
        "27",
    ),
    (
        "articulo_constitucional",
        "los artículos 14 y 16 constitucionales garantizan",
        "14",
    ),
]

SECONDARY_TEST_CASES = [
    (
        "sin_perjuicio",
        "sin perjuicio de lo dispuesto en la Ley Federal del Trabajo respecto a los contratos",
        "Ley Federal del Trabajo",
    ),
    (
        "para_efectos",
        "para los efectos de la Ley de Instituciones de Crédito, se entenderá por",
        "Ley de Instituciones de Crédito",
    ),
]


# ============================================================
# Tests
# ============================================================

class TestPrimaryPatterns:
    """Test that primary citation patterns correctly extract law names."""

    def _find_pattern(self, name: str):
        """Find a pattern by name."""
        for p in PRIMARY_PATTERNS:
            if p["name"] == name:
                return p
        return None

    @pytest.mark.parametrize("pattern_name,text,expected", PRIMARY_TEST_CASES)
    def test_primary_pattern_matches(self, pattern_name, text, expected):
        pat_info = self._find_pattern(pattern_name)
        assert pat_info is not None, f"Pattern '{pattern_name}' not found"

        matches = list(pat_info["pattern"].finditer(text))
        assert len(matches) > 0, (
            f"Pattern '{pattern_name}' did not match in: {text!r}"
        )

        matched_text = matches[0].group(1)
        assert expected.lower() in matched_text.lower(), (
            f"Expected '{expected}' in matched text '{matched_text}' "
            f"for pattern '{pattern_name}'"
        )

    def test_all_primary_patterns_have_required_fields(self):
        for pat in PRIMARY_PATTERNS:
            assert "name" in pat, f"Pattern missing 'name': {pat}"
            assert "pattern" in pat, f"Pattern missing 'pattern': {pat}"
            assert "confidence" in pat, f"Pattern missing 'confidence': {pat}"
            assert pat["confidence"] in ("high", "medium", "low")
            assert pat["pattern"] is not None

    def test_primary_patterns_no_false_positives_on_self_reference(self):
        """Should not match 'esta Ley' or 'la presente Ley' as a foreign law name."""
        false_positive_texts = [
            "conforme a lo dispuesto en esta Ley, el sujeto",
            "lo previsto en la presente Ley será aplicable",
        ]
        for text in false_positive_texts:
            for pat_info in PRIMARY_PATTERNS:
                matches = list(pat_info["pattern"].finditer(text))
                for m in matches:
                    raw = m.group(1) if m.lastindex >= 1 else ""
                    assert "esta" not in raw.lower(), (
                        f"Pattern '{pat_info['name']}' matched self-reference: '{raw}'"
                    )


class TestConstitutionalPatterns:
    """Test constitutional reference patterns."""

    def _find_pattern(self, name: str):
        for p in CONSTITUTIONAL_PATTERNS:
            if p["name"] == name:
                return p
        return None

    @pytest.mark.parametrize("pattern_name,text,expected_article", CONSTITUTIONAL_TEST_CASES)
    def test_constitutional_pattern_matches(self, pattern_name, text, expected_article):
        pat_info = self._find_pattern(pattern_name)
        assert pat_info is not None, f"Pattern '{pattern_name}' not found"

        matches = list(pat_info["pattern"].finditer(text))
        assert len(matches) > 0, (
            f"Pattern '{pattern_name}' did not match in: {text!r}"
        )

        if pat_info["pattern"].groups >= 1:
            article_text = matches[0].group(1)
            assert expected_article in article_text, (
                f"Expected article '{expected_article}' in '{article_text}'"
            )

    def test_constitutional_patterns_have_target(self):
        for pat in CONSTITUTIONAL_PATTERNS:
            assert "target" in pat
            assert pat["target"] == "constitucion-politica"


class TestSecondaryPatterns:
    """Test secondary citation patterns."""

    def _find_pattern(self, name: str):
        for p in SECONDARY_PATTERNS:
            if p["name"] == name:
                return p
        return None

    @pytest.mark.parametrize("pattern_name,text,expected", SECONDARY_TEST_CASES)
    def test_secondary_pattern_matches(self, pattern_name, text, expected):
        pat_info = self._find_pattern(pattern_name)
        assert pat_info is not None, f"Pattern '{pattern_name}' not found"

        matches = list(pat_info["pattern"].finditer(text))
        assert len(matches) > 0, (
            f"Pattern '{pattern_name}' did not match in: {text!r}"
        )

        matched_text = matches[0].group(1)
        assert expected.lower() in matched_text.lower(), (
            f"Expected '{expected}' in '{matched_text}'"
        )


class TestCleanLawName:
    """Test the clean_law_name utility function."""

    def test_removes_trailing_conjunction(self):
        raw = "Ley Federal del Trabajo y sus reglamentos"
        cleaned = clean_law_name(raw)
        assert "y sus" not in cleaned

    def test_removes_trailing_punctuation(self):
        raw = "Ley del Seguro Social,"
        cleaned = clean_law_name(raw)
        assert cleaned.endswith("Social")

    def test_strips_whitespace(self):
        raw = "  Ley de Aguas Nacionales  "
        cleaned = clean_law_name(raw)
        assert cleaned == "Ley de Aguas Nacionales"

    def test_preserves_law_name(self):
        raw = "Ley General de Salud"
        cleaned = clean_law_name(raw)
        assert cleaned == "Ley General de Salud"

    def test_removes_trailing_vigente(self):
        raw = "Ley Aduanera vigente"
        cleaned = clean_law_name(raw)
        assert "vigente" not in cleaned


class TestExtractArticleNumber:
    """Test the extract_article_number utility function."""

    def test_basic_article(self):
        text = "artículo 5 de la Ley Federal del Trabajo"
        result = extract_article_number(text)
        assert result == "5"

    def test_article_with_fraction(self):
        text = "artículo 123-A de la Constitución"
        result = extract_article_number(text)
        assert result == "123-A"

    def test_no_article(self):
        text = "conforme a la Ley General de Salud"
        result = extract_article_number(text)
        assert result is None

    def test_multiple_articles_returns_first(self):
        text = "artículo 14 y artículo 16 constitucionales"
        result = extract_article_number(text)
        assert result == "14"


class TestPatternCoverage:
    """Test pattern coverage on a sample multi-citation article."""

    SAMPLE_ARTICLE = """
    Artículo 10. Para los efectos de la presente Ley, la autoridad competente
    deberá actuar conforme a lo dispuesto en el Código Fiscal de la Federación
    y de conformidad con la Ley Federal de Procedimiento Administrativo.
    En lo no previsto, serán aplicables las disposiciones de la Ley de Amparo,
    Reglamentaria de los Artículos 103 y 107 de la Constitución Política de
    los Estados Unidos Mexicanos, así como lo establecido en la Ley General
    de Transparencia y Acceso a la Información Pública.
    """

    def test_sample_article_yields_multiple_citations(self):
        all_matches = []
        for pat_info in PRIMARY_PATTERNS + SECONDARY_PATTERNS:
            for m in pat_info["pattern"].finditer(self.SAMPLE_ARTICLE):
                all_matches.append((pat_info["name"], m.group(1)))

        # Should find at least 3 distinct law references
        assert len(all_matches) >= 3, (
            f"Expected at least 3 matches, got {len(all_matches)}: {all_matches}"
        )

    def test_constitutional_reference_detected(self):
        matches = []
        for pat_info in CONSTITUTIONAL_PATTERNS:
            matches.extend(pat_info["pattern"].finditer(self.SAMPLE_ARTICLE))

        assert len(matches) >= 1, "Constitutional reference not detected in sample article"
