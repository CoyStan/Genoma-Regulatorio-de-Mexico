"""Utility helpers for legal dependency taxonomy classification.

This module centralizes inspectable heuristic rules so they can be reused
by reporting scripts and improved over time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TaxonomyRule:
    dependency_type: str
    dependency_subtype: str
    strength: str
    pattern: re.Pattern[str]
    explanation: str


_RULES: list[TaxonomyRule] = [
    TaxonomyRule(
        dependency_type="definitional",
        dependency_subtype="term_definition_reference",
        strength="strong",
        pattern=re.compile(r"\b(?:se entender[aá]|para efectos de|definid[oa]|definiciones?)\b", re.IGNORECASE),
        explanation="El contexto sugiere remisión para interpretar definiciones o conceptos.",
    ),
    TaxonomyRule(
        dependency_type="procedural",
        dependency_subtype="adjudication_or_process",
        strength="strong",
        pattern=re.compile(r"\b(?:procedimiento|tr[aá]mite|recurso|juicio|audiencia|plazo)\b", re.IGNORECASE),
        explanation="El texto vincula reglas de trámite, proceso o medios de defensa.",
    ),
    TaxonomyRule(
        dependency_type="supletory",
        dependency_subtype="supplementary_application",
        strength="strong",
        pattern=re.compile(r"\b(?:supletoriamente|de manera supletoria|en lo no previsto)\b", re.IGNORECASE),
        explanation="La cita opera como norma supletoria cuando la ley principal no regula un punto.",
    ),
    TaxonomyRule(
        dependency_type="institutional",
        dependency_subtype="authority_competence",
        strength="medium",
        pattern=re.compile(r"\b(?:competencia|atribuci[oó]n|facultad(?:es)?|autoridad|secretar[ií]a|comisi[oó]n)\b", re.IGNORECASE),
        explanation="La referencia conecta competencias o atribuciones institucionales.",
    ),
    TaxonomyRule(
        dependency_type="sanctioning",
        dependency_subtype="penalty_or_liability",
        strength="strong",
        pattern=re.compile(r"\b(?:sanci[oó]n|multa|pena|responsabilidad|infracci[oó]n|delito)\b", re.IGNORECASE),
        explanation="El contexto vincula consecuencias sancionatorias o de responsabilidad.",
    ),
    TaxonomyRule(
        dependency_type="fiscal_financial",
        dependency_subtype="tax_budget_or_payment",
        strength="medium",
        pattern=re.compile(r"\b(?:impuesto|contribuci[oó]n|fiscal|presupuesto|egresos|ingresos|derechos?\s+fiscales?)\b", re.IGNORECASE),
        explanation="La cita incide en obligaciones fiscales, presupuestarias o financieras.",
    ),
    TaxonomyRule(
        dependency_type="implementation_operative",
        dependency_subtype="regulatory_implementation",
        strength="medium",
        pattern=re.compile(r"\b(?:reglamento|lineamientos|normas oficiales|aplicaci[oó]n|ejecuci[oó]n)\b", re.IGNORECASE),
        explanation="Se trata de una referencia operativa para implementación normativa.",
    ),
    TaxonomyRule(
        dependency_type="constitutional_grounding",
        dependency_subtype="constitutional_basis",
        strength="strong",
        pattern=re.compile(r"\b(?:constituci[oó]n|cpeum|art[ií]culo\s+\d+\s+constitucional|derechos humanos)\b", re.IGNORECASE),
        explanation="La referencia aporta fundamento constitucional o de control constitucional.",
    ),
]


def classify_dependency(citation: dict) -> dict:
    """Classify a citation into a legal dependency taxonomy using heuristics."""
    text = f"{citation.get('citation_text', '')} {citation.get('target_law_raw', '')} {citation.get('pattern_name', '')}".strip()
    text = re.sub(r"\s+", " ", text)

    for rule in _RULES:
        if rule.pattern.search(text):
            return {
                "dependency_type": rule.dependency_type,
                "dependency_subtype": rule.dependency_subtype,
                "dependency_strength": rule.strength,
                "resolution_method": "heuristic_rule",
                "explanation": rule.explanation,
                "confidence": "high" if rule.strength == "strong" else "medium",
            }

    return {
        "dependency_type": "generic_unresolved",
        "dependency_subtype": "general_cross_reference",
        "dependency_strength": "weak",
        "resolution_method": "fallback",
        "explanation": "No se detectó un patrón semántico claro; requiere revisión legal.",
        "confidence": "low",
    }


def infer_corpus_layer(law_meta: dict) -> str:
    """Infer legal corpus layer for prioritization outputs."""
    name = (law_meta.get("name") or "").lower()
    short = (law_meta.get("short_name") or "").lower()
    full = f"{name} {short}"

    if "constituci" in full or "reglamento" in full or "código" in full or "ley" in full:
        return "layer_1_normative_core"
    if any(token in full for token in ["decreto", "transitorio", "acuerdo"]):
        return "layer_2_change_layer"
    return "layer_3_interpretive_prepared"
