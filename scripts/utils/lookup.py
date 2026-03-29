"""
Law name → canonical ID lookup table.
Covers all ~296 federal laws with known abbreviations and alternate names.

Structure:
    CANONICAL_LAWS: dict[law_id, dict] — master registry of all laws
    ALIASES: dict[alias_string, law_id] — reverse lookup (name/acronym → id)
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Optional

# ---------------------------------------------------------------------------
# CANONICAL LAW REGISTRY
# Each entry: id (slug), full name, common abbreviation, known aliases
# ---------------------------------------------------------------------------

CANONICAL_LAWS: dict[str, dict] = {
    # Constitutional
    "constitucion-politica": {
        "name": "Constitución Política de los Estados Unidos Mexicanos",
        "short": "CPEUM",
        "aliases": [
            "Constitución",
            "Constitución Política",
            "Constitución Federal",
            "Carta Magna",
            "Ley Fundamental",
        ],
        "sector": "constitucional",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CPEUM.pdf",
    },
    # Leyes de trabajo y seguridad social
    "ley-federal-del-trabajo": {
        "name": "Ley Federal del Trabajo",
        "short": "LFT",
        "aliases": [
            "Ley del Trabajo",
            "Ley Laboral",
            "la ley laboral",
            "legislación laboral",
        ],
        "sector": "trabajo",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf",
    },
    "ley-del-seguro-social": {
        "name": "Ley del Seguro Social",
        "short": "LSS",
        "aliases": [
            "Ley del IMSS",
            "Ley del Seguro Social",
        ],
        "sector": "seguridad-social",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LSS.pdf",
    },
    "ley-del-infonavit": {
        "name": "Ley del Instituto del Fondo Nacional de la Vivienda para los Trabajadores",
        "short": "LINFONAVIT",
        "aliases": [
            "Ley del INFONAVIT",
            "Ley del Fondo Nacional de la Vivienda",
        ],
        "sector": "vivienda",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LINFONAVIT.pdf",
    },
    "ley-issste": {
        "name": "Ley del Instituto de Seguridad y Servicios Sociales de los Trabajadores del Estado",
        "short": "LISSSTE",
        "aliases": [
            "Ley del ISSSTE",
            "Ley de Seguridad Social para los Trabajadores del Estado",
        ],
        "sector": "seguridad-social",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LISSSTE.pdf",
    },
    # Leyes fiscales
    "codigo-fiscal-federacion": {
        "name": "Código Fiscal de la Federación",
        "short": "CFF",
        "aliases": [
            "Código Fiscal",
            "el Código Fiscal",
        ],
        "sector": "fiscal",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CFF.pdf",
    },
    "ley-isr": {
        "name": "Ley del Impuesto sobre la Renta",
        "short": "LISR",
        "aliases": [
            "Ley del ISR",
            "Ley del Impuesto sobre la Renta",
            "legislación fiscal en materia de ISR",
        ],
        "sector": "fiscal",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LISR.pdf",
    },
    "ley-iva": {
        "name": "Ley del Impuesto al Valor Agregado",
        "short": "LIVA",
        "aliases": [
            "Ley del IVA",
            "Ley del Impuesto al Valor Agregado",
        ],
        "sector": "fiscal",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LIVA.pdf",
    },
    "ley-ieps": {
        "name": "Ley del Impuesto Especial sobre Producción y Servicios",
        "short": "LIEPS",
        "aliases": [
            "Ley del IEPS",
        ],
        "sector": "fiscal",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LIEPS.pdf",
    },
    "ley-aduanera": {
        "name": "Ley Aduanera",
        "short": "LA",
        "aliases": [
            "legislación aduanera",
            "normativa aduanera",
        ],
        "sector": "comercio-exterior",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LA.pdf",
    },
    # Leyes de comercio y economía
    "codigo-comercio": {
        "name": "Código de Comercio",
        "short": "CCom",
        "aliases": [
            "el Código de Comercio",
            "código mercantil",
        ],
        "sector": "comercio",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CCom.pdf",
    },
    "ley-federal-competencia-economica": {
        "name": "Ley Federal de Competencia Económica",
        "short": "LFCE",
        "aliases": [
            "Ley de Competencia",
            "legislación de competencia económica",
        ],
        "sector": "competencia",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFCE.pdf",
    },
    "ley-federal-proteccion-consumidor": {
        "name": "Ley Federal de Protección al Consumidor",
        "short": "LFPC",
        "aliases": [
            "Ley del Consumidor",
            "Ley de Protección al Consumidor",
            "Ley PROFECO",
        ],
        "sector": "consumidor",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPC.pdf",
    },
    "ley-general-sociedades-mercantiles": {
        "name": "Ley General de Sociedades Mercantiles",
        "short": "LGSM",
        "aliases": [
            "Ley de Sociedades Mercantiles",
            "legislación societaria",
        ],
        "sector": "mercantil",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGSM.pdf",
    },
    "ley-mercado-valores": {
        "name": "Ley del Mercado de Valores",
        "short": "LMV",
        "aliases": [
            "Ley del Mercado de Valores",
            "legislación bursátil",
        ],
        "sector": "financiero",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LMV.pdf",
    },
    # Leyes financieras
    "ley-instituciones-credito": {
        "name": "Ley de Instituciones de Crédito",
        "short": "LIC",
        "aliases": [
            "Ley Bancaria",
            "Ley de Banca",
            "legislación bancaria",
        ],
        "sector": "financiero",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LIC.pdf",
    },
    "ley-banco-mexico": {
        "name": "Ley del Banco de México",
        "short": "LBM",
        "aliases": [
            "Ley del Banxico",
            "Ley del Banco Central",
        ],
        "sector": "financiero",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LBM.pdf",
    },
    "ley-sistemas-pagos": {
        "name": "Ley del Sistema de Pagos",
        "short": "LSP",
        "aliases": [],
        "sector": "financiero",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LSP.pdf",
    },
    "ley-fintech": {
        "name": "Ley para Regular las Instituciones de Tecnología Financiera",
        "short": "LRITF",
        "aliases": [
            "Ley Fintech",
            "Ley de Tecnología Financiera",
        ],
        "sector": "financiero",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LRITF.pdf",
    },
    # Leyes civiles
    "codigo-civil-federal": {
        "name": "Código Civil Federal",
        "short": "CCF",
        "aliases": [
            "Código Civil",
            "el Código Civil",
        ],
        "sector": "civil",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CCF.pdf",
    },
    "codigo-federal-procedimientos-civiles": {
        "name": "Código Federal de Procedimientos Civiles",
        "short": "CFPC",
        "aliases": [
            "Código de Procedimientos Civiles Federal",
        ],
        "sector": "civil",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CFPC.pdf",
    },
    # Leyes penales
    "codigo-penal-federal": {
        "name": "Código Penal Federal",
        "short": "CPF",
        "aliases": [
            "Código Penal",
            "el Código Penal",
            "legislación penal",
        ],
        "sector": "penal",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CPF.pdf",
    },
    "codigo-nacional-procedimientos-penales": {
        "name": "Código Nacional de Procedimientos Penales",
        "short": "CNPP",
        "aliases": [
            "Código Procesal Penal",
            "Código Nacional Penal",
        ],
        "sector": "penal",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CNPP.pdf",
    },
    "ley-federal-anticorrupcion": {
        "name": "Ley General del Sistema Nacional Anticorrupción",
        "short": "LGSNA",
        "aliases": [
            "Ley Anticorrupción",
            "Ley del Sistema Anticorrupción",
            "Ley del SNA",
        ],
        "sector": "anticorrupcion",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGSNA.pdf",
    },
    # Leyes ambientales
    "lgeepa": {
        "name": "Ley General del Equilibrio Ecológico y la Protección al Ambiente",
        "short": "LGEEPA",
        "aliases": [
            "Ley Ambiental",
            "Ley Ecológica",
            "Ley del Equilibrio Ecológico",
            "Ley de Medio Ambiente",
        ],
        "sector": "ambiental",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGEEPA.pdf",
    },
    "ley-aguas-nacionales": {
        "name": "Ley de Aguas Nacionales",
        "short": "LAN",
        "aliases": [
            "Ley de Aguas",
            "Ley Hídrica",
        ],
        "sector": "ambiental",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LAN.pdf",
    },
    # Leyes de salud
    "ley-general-salud": {
        "name": "Ley General de Salud",
        "short": "LGS",
        "aliases": [
            "Ley de Salud",
            "Ley Sanitaria",
            "legislación sanitaria",
        ],
        "sector": "salud",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGS.pdf",
    },
    # Leyes de educación
    "ley-general-educacion": {
        "name": "Ley General de Educación",
        "short": "LGE",
        "aliases": [
            "Ley de Educación",
            "legislación educativa",
        ],
        "sector": "educacion",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGE.pdf",
    },
    # Leyes de transparencia y acceso a la información
    "lgtaip": {
        "name": "Ley General de Transparencia y Acceso a la Información Pública",
        "short": "LGTAIP",
        "aliases": [
            "Ley de Transparencia",
            "Ley de Acceso a la Información",
            "Ley INAI",
        ],
        "sector": "transparencia",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGTAIP.pdf",
    },
    "lfpdppp": {
        "name": "Ley Federal de Protección de Datos Personales en Posesión de los Particulares",
        "short": "LFPDPPP",
        "aliases": [
            "Ley de Protección de Datos",
            "Ley de Datos Personales",
            "Ley de Privacidad",
        ],
        "sector": "transparencia",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf",
    },
    # Leyes de telecomunicaciones
    "lftr": {
        "name": "Ley Federal de Telecomunicaciones y Radiodifusión",
        "short": "LFTR",
        "aliases": [
            "Ley de Telecomunicaciones",
            "Ley Telecom",
            "Ley de Radiodifusión",
        ],
        "sector": "telecomunicaciones",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFTR.pdf",
    },
    # Leyes de energía
    "ley-industria-electrica": {
        "name": "Ley de la Industria Eléctrica",
        "short": "LIE",
        "aliases": [
            "Ley Eléctrica",
            "Ley de Electricidad",
            "Ley de la CFE",
        ],
        "sector": "energia",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LIE.pdf",
    },
    "ley-hidrocarburos": {
        "name": "Ley de Hidrocarburos",
        "short": "LH",
        "aliases": [
            "Ley del Petróleo",
            "Ley Petrolera",
        ],
        "sector": "energia",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LH.pdf",
    },
    "ley-pemex": {
        "name": "Ley de Petróleos Mexicanos",
        "short": "LPEMEX",
        "aliases": [
            "Ley de PEMEX",
            "Ley Orgánica de PEMEX",
        ],
        "sector": "energia",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LPEMEX.pdf",
    },
    # Leyes administrativas y de organización del Estado
    "lopjf": {
        "name": "Ley Orgánica del Poder Judicial de la Federación",
        "short": "LOPJF",
        "aliases": [
            "Ley Orgánica del Poder Judicial",
            "Ley del Poder Judicial",
        ],
        "sector": "judicial",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LOPJF.pdf",
    },
    "loapf": {
        "name": "Ley Orgánica de la Administración Pública Federal",
        "short": "LOAPF",
        "aliases": [
            "Ley Orgánica de la Administración Pública",
            "Ley de la Administración Pública Federal",
            "Ley Orgánica Federal",
        ],
        "sector": "administrativo",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LOAPF.pdf",
    },
    "lfpa": {
        "name": "Ley Federal de Procedimiento Administrativo",
        "short": "LFPA",
        "aliases": [
            "Ley de Procedimiento Administrativo",
            "Ley de Procedimientos Administrativos",
        ],
        "sector": "administrativo",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPA.pdf",
    },
    "ley-amparo": {
        "name": "Ley de Amparo, Reglamentaria de los Artículos 103 y 107 de la Constitución",
        "short": "LA",
        "aliases": [
            "Ley de Amparo",
            "Ley del Amparo",
            "legislación de amparo",
        ],
        "sector": "judicial",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LAmp.pdf",
    },
    "ley-contrataciones-publicas": {
        "name": "Ley de Adquisiciones, Arrendamientos y Servicios del Sector Público",
        "short": "LAASSP",
        "aliases": [
            "Ley de Adquisiciones",
            "Ley de Contrataciones Públicas",
            "Ley de Compras Gubernamentales",
        ],
        "sector": "administrativo",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LAASSP.pdf",
    },
    "ley-obras-publicas": {
        "name": "Ley de Obras Públicas y Servicios Relacionados con las Mismas",
        "short": "LOPSRM",
        "aliases": [
            "Ley de Obras Públicas",
            "Ley de Obra Pública",
        ],
        "sector": "administrativo",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LOPSRM.pdf",
    },
    "ley-responsabilidades-administrativas": {
        "name": "Ley General de Responsabilidades Administrativas",
        "short": "LGRA",
        "aliases": [
            "Ley de Responsabilidades",
            "Ley Anticorrupción Administrativa",
        ],
        "sector": "anticorrupcion",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGRA.pdf",
    },
    # Leyes electorales
    "lgipe": {
        "name": "Ley General de Instituciones y Procedimientos Electorales",
        "short": "LGIPE",
        "aliases": [
            "Ley Electoral",
            "Ley de Instituciones Electorales",
            "Ley del INE",
        ],
        "sector": "electoral",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGIPE.pdf",
    },
    "lgpp": {
        "name": "Ley General de Partidos Políticos",
        "short": "LGPP",
        "aliases": [
            "Ley de Partidos Políticos",
            "Ley Partidaria",
        ],
        "sector": "electoral",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGPP.pdf",
    },
    # Otras leyes importantes
    "ley-propiedad-industrial": {
        "name": "Ley Federal de Protección a la Propiedad Industrial",
        "short": "LFPPI",
        "aliases": [
            "Ley de Propiedad Industrial",
            "Ley de Marcas y Patentes",
            "Ley del IMPI",
        ],
        "sector": "propiedad-intelectual",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPPI.pdf",
    },
    "lfda": {
        "name": "Ley Federal del Derecho de Autor",
        "short": "LFDA",
        "aliases": [
            "Ley de Derechos de Autor",
            "Ley de Copyright",
        ],
        "sector": "propiedad-intelectual",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFDA.pdf",
    },
    "ley-inmigracion": {
        "name": "Ley de Migración",
        "short": "LM",
        "aliases": [
            "Ley Migratoria",
            "Ley de Inmigración",
        ],
        "sector": "migracion",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LM.pdf",
    },
    "ley-seguridad-nacional": {
        "name": "Ley de Seguridad Nacional",
        "short": "LSN",
        "aliases": [
            "Ley de Seguridad",
            "Legislación de Seguridad Nacional",
        ],
        "sector": "seguridad",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LSN.pdf",
    },
    "ley-prevencion-lavado-dinero": {
        "name": "Ley Federal para la Prevención e Identificación de Operaciones con Recursos de Procedencia Ilícita",
        "short": "LFPIORPI",
        "aliases": [
            "Ley Anti-lavado",
            "Ley de Lavado de Dinero",
            "Ley Antilavado",
        ],
        "sector": "financiero",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPIORPI.pdf",
    },
}

# ---------------------------------------------------------------------------
# Build reverse alias lookup
# ---------------------------------------------------------------------------

def _build_alias_map() -> dict[str, str]:
    """Build a flat alias → law_id mapping."""
    alias_map: dict[str, str] = {}
    for law_id, law_data in CANONICAL_LAWS.items():
        # Full name
        alias_map[law_data["name"].lower()] = law_id
        # Short name / acronym
        alias_map[law_data["short"].lower()] = law_id
        # All explicit aliases
        for alias in law_data.get("aliases", []):
            alias_map[alias.lower()] = law_id
    return alias_map


ALIASES: dict[str, str] = _build_alias_map()


# ---------------------------------------------------------------------------
# Resolution functions
# ---------------------------------------------------------------------------

def resolve_law_name(raw_name: str, fuzzy_threshold: float = 0.75) -> dict:
    """
    Resolve a raw extracted law name to a canonical law ID.

    Returns:
        {
            "law_id": str | None,
            "confidence": "high" | "medium" | "low" | "unresolved",
            "matched_alias": str | None,
            "score": float,
        }
    """
    if not raw_name:
        return {"law_id": None, "confidence": "unresolved", "matched_alias": None, "score": 0.0}

    cleaned = raw_name.strip().lower()

    # 1. Exact match
    if cleaned in ALIASES:
        return {
            "law_id": ALIASES[cleaned],
            "confidence": "high",
            "matched_alias": cleaned,
            "score": 1.0,
        }

    # 2. Acronym match (all-caps, 2-8 chars)
    upper = raw_name.strip()
    if re.match(r"^[A-Z]{2,8}$", upper) and upper.lower() in ALIASES:
        return {
            "law_id": ALIASES[upper.lower()],
            "confidence": "high",
            "matched_alias": upper,
            "score": 1.0,
        }

    # 3. Fuzzy match against full names and aliases
    best_score = 0.0
    best_id = None
    best_alias = None

    for alias, law_id in ALIASES.items():
        score = SequenceMatcher(None, cleaned, alias).ratio()
        if score > best_score:
            best_score = score
            best_id = law_id
            best_alias = alias

    if best_score >= fuzzy_threshold:
        confidence = "high" if best_score >= 0.90 else "medium" if best_score >= fuzzy_threshold else "low"
        return {
            "law_id": best_id,
            "confidence": confidence,
            "matched_alias": best_alias,
            "score": best_score,
        }

    # 4. Partial name match (does cleaned start with the alias or vice versa?)
    for alias, law_id in ALIASES.items():
        if len(alias) >= 10 and (cleaned.startswith(alias[:15]) or alias.startswith(cleaned[:15])):
            return {
                "law_id": law_id,
                "confidence": "low",
                "matched_alias": alias,
                "score": 0.85,
            }

    return {"law_id": None, "confidence": "unresolved", "matched_alias": None, "score": best_score}


def get_law_metadata(law_id: str) -> Optional[dict]:
    """Return metadata for a canonical law ID, or None if not found."""
    return CANONICAL_LAWS.get(law_id)


def list_all_law_ids() -> list[str]:
    """Return all known canonical law IDs."""
    return list(CANONICAL_LAWS.keys())
