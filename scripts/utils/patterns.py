"""
Regex patterns for extracting legal citations from Mexican federal laws.
All patterns are designed for Spanish-language legal text.
"""

import re

# ---------------------------------------------------------------------------
# PRIMARY PATTERNS (high confidence)
# These match formulaic phrases used in Mexican legal drafting.
# ---------------------------------------------------------------------------

PRIMARY_PATTERNS = [
    # "conforme a lo dispuesto en/por la [Ley]"
    {
        "name": "conforme_dispuesto",
        "pattern": re.compile(
            r"conforme\s+a\s+lo\s+dispuesto\s+(?:en|por)\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
    # "en términos de lo establecido en/por la [Ley]"
    {
        "name": "terminos_establecido",
        "pattern": re.compile(
            r"en\s+t[eé]rminos\s+de\s+lo\s+establecido\s+(?:en|por)\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
    # "de acuerdo con la [Ley]"
    {
        "name": "de_acuerdo",
        "pattern": re.compile(
            r"de\s+acuerdo\s+con\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
    # "lo previsto en la [Ley]"
    {
        "name": "lo_previsto",
        "pattern": re.compile(
            r"lo\s+previsto\s+en\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
    # "con fundamento en el artículo [N] de la [Ley]"
    {
        "name": "fundamento_articulo",
        "pattern": re.compile(
            r"con\s+fundamento\s+en\s+(?:el|los|la|las)\s+art[ií]culo[s]?\s+"
            r"[\d\w,\s]+\s+de\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
    # "de conformidad con la [Ley]"
    {
        "name": "conformidad",
        "pattern": re.compile(
            r"de\s+conformidad\s+con\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
    # "en los términos de la [Ley]"
    {
        "name": "en_los_terminos",
        "pattern": re.compile(
            r"en\s+(?:los|las)\s+t[eé]rminos\s+de\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
    # "a que se refiere la [Ley]"
    {
        "name": "a_que_refiere",
        "pattern": re.compile(
            r"a\s+que\s+se\s+refiere\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
    # "lo dispuesto por la [Ley]"
    {
        "name": "lo_dispuesto",
        "pattern": re.compile(
            r"lo\s+dispuesto\s+(?:por|en)\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
    # "prevista en la [Ley]"
    {
        "name": "prevista_en",
        "pattern": re.compile(
            r"previst[ao]s?\s+en\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
    # "establecida en la [Ley]"
    {
        "name": "establecida_en",
        "pattern": re.compile(
            r"establecid[ao]s?\s+en\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
    # "regulada por la [Ley]"
    {
        "name": "regulada_por",
        "pattern": re.compile(
            r"regulad[ao]s?\s+(?:por|en)\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
    # "señalada en la [Ley]"
    {
        "name": "senalada_en",
        "pattern": re.compile(
            r"se[ñn]alad[ao]s?\s+en\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "high",
    },
]

# ---------------------------------------------------------------------------
# SECONDARY PATTERNS (medium confidence)
# ---------------------------------------------------------------------------

SECONDARY_PATTERNS = [
    # "la [Ley] y sus reglamentos"
    {
        "name": "ley_y_reglamentos",
        "pattern": re.compile(
            r"(?:la|el)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)"
            r"\s+y\s+sus\s+reglamentos",
            re.IGNORECASE,
        ),
        "confidence": "medium",
    },
    # "sin perjuicio de lo dispuesto en la [Ley]"
    {
        "name": "sin_perjuicio",
        "pattern": re.compile(
            r"sin\s+perjuicio\s+de\s+lo\s+dispuesto\s+en\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "medium",
    },
    # "para los efectos de la [Ley]"
    {
        "name": "para_efectos",
        "pattern": re.compile(
            r"para\s+(?:los|las)\s+efectos\s+de\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "medium",
    },
    # "en materia de [topic] conforme a la [Ley]"
    {
        "name": "materia_conforme",
        "pattern": re.compile(
            r"en\s+materia\s+de\s+\w+\s+conforme\s+a\s+(?:la|el|los|las)\s+"
            r"((?:Ley|Código|Reglamento|Decreto|Estatuto|Acuerdo)\s+[A-ZÁÉÍÓÚÜÑ][^,;.()]{3,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "medium",
    },
    # Direct law name mention preceded by article
    {
        "name": "direct_mention",
        "pattern": re.compile(
            r"\b(?:la|el)\s+"
            r"((?:Ley|Código|Reglamento|Decreto)\s+(?:Federal|General|Nacional|Orgánica|Orgánico|de|del|para|sobre|en)\s+"
            r"[A-ZÁÉÍÓÚÜÑ][^,;.()]{5,120}?)(?=[,;.()\n]|$)",
            re.IGNORECASE,
        ),
        "confidence": "medium",
    },
]

# ---------------------------------------------------------------------------
# CONSTITUTIONAL REFERENCES
# ---------------------------------------------------------------------------

CONSTITUTIONAL_PATTERNS = [
    # "artículo [N] de la Constitución Política de los Estados Unidos Mexicanos"
    {
        "name": "constitucion_full",
        "pattern": re.compile(
            r"art[ií]culo[s]?\s+([\d\w,\s]+)\s+de\s+la\s+Constituci[oó]n\s+Pol[ií]tica\s+"
            r"de\s+los\s+Estados\s+Unidos\s+Mexicanos",
            re.IGNORECASE,
        ),
        "confidence": "high",
        "target": "constitucion-politica",
    },
    # "artículo [N] constitucional"
    {
        "name": "articulo_constitucional",
        "pattern": re.compile(
            r"art[ií]culo[s]?\s+([\d\w,\s]+)\s+constitucional(?:es)?",
            re.IGNORECASE,
        ),
        "confidence": "high",
        "target": "constitucion-politica",
    },
    # "la Constitución" (bare reference)
    {
        "name": "constitucion_bare",
        "pattern": re.compile(
            r"\b(?:la|La)\s+Constituci[oó]n\b(?!\s+Pol[ií]tica\s+de\s+(?!los\s+Estados\s+Unidos\s+Mexicanos))",
            re.IGNORECASE,
        ),
        "confidence": "medium",
        "target": "constitucion-politica",
    },
]

# ---------------------------------------------------------------------------
# ARTICLE REFERENCE PATTERNS (to extract source/target article numbers)
# ---------------------------------------------------------------------------

ARTICLE_PATTERN = re.compile(
    r"art[ií]culo[s]?\s+([\d][\d\w\-,\s]{0,30}?)(?=\s+(?:de\s+(?:la|el|los|las)|fracción|párrafo|bis|ter))",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# DEFINITION PATTERNS
# ---------------------------------------------------------------------------

DEFINITION_PATTERNS = [
    re.compile(
        r"Para\s+(?:los\s+)?efectos\s+de\s+(?:esta\s+Ley|la\s+presente\s+Ley|este\s+C[oó]digo|el\s+presente\s+C[oó]digo)[,:]",
        re.IGNORECASE,
    ),
    re.compile(
        r"Para\s+efectos\s+de\s+(?:esta\s+Ley|la\s+presente\s+Ley)[,:]",
        re.IGNORECASE,
    ),
    re.compile(
        r"Se\s+entiende\s+(?:por|como)\s+",
        re.IGNORECASE,
    ),
    re.compile(
        r"Se\s+considera[rá]*\s+(?:\w+\s+){1,4}(?:a|como)\s+",
        re.IGNORECASE,
    ),
    re.compile(
        r"Para\s+los\s+efectos\s+(?:del|de\s+los)\s+art[ií]culo[s]?\s+[\d\w,\s]+[,:]",
        re.IGNORECASE,
    ),
]

# Acronym pattern: matches things like "LFT", "CPEUM", "LSS", "LISR"
ACRONYM_PATTERN = re.compile(r"\b([A-Z]{2,8})\b")


def extract_article_number(text: str) -> str | None:
    """Extract article number from a text snippet."""
    match = re.search(r"art[ií]culo[s]?\s+(\d+[\w\-]*)", text, re.IGNORECASE)
    return match.group(1) if match else None


def clean_law_name(raw_name: str) -> str:
    """Normalize a raw extracted law name."""
    name = raw_name.strip()
    # Remove trailing common words that bleed into matches
    name = re.sub(
        r"\s+(?:y\s+sus|en\s+materia|así\s+como|entre\s+otros|entre\s+otras|vigente|aplicable).*$",
        "",
        name,
        flags=re.IGNORECASE,
    )
    # Remove trailing whitespace and punctuation
    name = name.rstrip(".,;: \t\n")
    return name
