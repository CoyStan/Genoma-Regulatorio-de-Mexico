# Genoma Regulatorio de México 🇲🇽

Plataforma de **inteligencia de dependencias normativas** y **análisis de impacto de reforma** para legislación federal mexicana.

> Rama de trabajo recomendada para este pivote: `pivot/legal-dependency-intelligence`.

> Enfoque principal: workflows para despachos medianos y top-tier en México (laboral, fiscal, regulatorio/administrativo, contratación pública/infraestructura, constitucional/amparo y monitoreo legislativo).

---

## Qué problema resuelve

Antes de redactar, litigar o asesorar una reforma, los equipos legales necesitan identificar:

- qué otras leyes/artículos se mueven cuando cambia una disposición,
- qué normas dependen de una definición,
- qué referencias están frágiles/no resueltas,
- qué bloques normativos conviene revisar de forma armónica.

Este repositorio conserva el backbone ETL/grafo original y lo extiende con una capa de **taxonomía de dependencias** y reportes lawyer-facing.

---

## Posicionamiento del producto

### Núcleo (primario)
- Trazabilidad de dependencias estatutarias.
- Análisis de impacto de reforma.
- Trazabilidad de definiciones.
- Detección de referencias frágiles/obsoletas.
- Candidatos de revisión armónica entre estatutos y reglamentos.

### Capa secundaria (exploratoria)
- Simplificación/abrogación/fusión normativa (se mantiene como análisis experimental de política pública, no como identidad central).

---

## Arquitectura de capas del corpus

- **Layer 1 — Núcleo normativo**: Constitución, leyes federales/generales/códigos y reglamentos federales clave.
- **Layer 2 — Capa de cambio**: decretos/acuerdos/transitorios y cadenas de reforma (base para modelar eventos de enmienda).
- **Layer 3 — Capa interpretativa (preparada)**: criterios/circulares DOF y tratados seleccionados (extensión futura).

Generador de capas:
```bash
python scripts/20_build_corpus_layers.py
```

---

## Pipeline

## 1) Infraestructura base (preservada)
```bash
python scripts/01_scrape.py
python scripts/02_parse.py
python scripts/03_extract_citations.py
python scripts/04_resolve_entities.py
python scripts/05_extract_definitions.py      # opcional
python scripts/06_build_graph.py
python scripts/07_diagnostics.py
python scripts/09_article_stats.py
python scripts/10_build_article_graph.py
```

## 2) Capa de dependencia legal (nueva)
```bash
python scripts/14_classify_dependencies.py
python scripts/15_reform_impact_report.py
python scripts/16_definition_trace.py
python scripts/17_harmonization_report.py
python scripts/18_reference_fragility.py
python scripts/19_validate_dependency_outputs.py
```

## 3) Capa exploratoria (secundaria)
```bash
python scripts/11_simplification_report.py
```

---

## Taxonomía de dependencias (heurística v1)

Cada cita resuelta se clasifica con campos auditables:

- `dependency_type`
- `dependency_subtype`
- `dependency_strength`
- `resolution_method`
- `explanation`
- `confidence`
- `entity_resolution_method`

Tipos iniciales:
- `definitional`
- `procedural`
- `supletory`
- `institutional`
- `sanctioning`
- `fiscal_financial`
- `implementation_operative`
- `constitutional_grounding`
- `generic_unresolved`

---

## Outputs clave

- `data/dependencies/dependencies.json`
- `data/dependencies/dependency_review_sample.csv`
- `data/dependencies/reform_impact_report.json`
- `data/dependencies/definition_trace_report.json`
- `data/dependencies/harmonization_report.json`
- `data/dependencies/reference_fragility_report.json`
- `data/graph/corpus_layers.json`

Entidad-resolución auditable:
- `data/lookup/resolution_log.json` (incluye `by_resolution_method`)
- `data/lookup/unresolved.json`

---

## Frontend (workflow-first, grafo como apoyo)

La interfaz mantiene la visualización 3D como soporte, pero prioriza workflows:
- búsqueda de ley/artículo,
- perfil de ley y de artículo,
- resumen de dependencias,
- impacto de reforma,
- trazabilidad de definiciones,
- referencias frágiles.

Para servir localmente:
```bash
cd docs && python -m http.server 8080
```

---

## Limitaciones actuales

- Clasificación de dependencias basada en reglas heurísticas (no sustituye análisis jurídico experto).
- Modelado de eventos de reforma en etapa incremental (capa 2 preparada, no exhaustiva).
- Cobertura interpretativa (criterios/circulares/tratados) no completada aún.
- Puede haber falsos positivos/negativos en extracción y resolución de citas.

---

## Instalación y tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

---

## Aviso

Este proyecto es infraestructura analítica para navegación y evaluación de arquitectura normativa.
**No constituye asesoría legal.**
