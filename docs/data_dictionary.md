# Diccionario de Datos — Genoma Regulatorio de México

## Archivos del pipeline

### `data/raw/<law_id>.json` — Ley raspada

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | string | Identificador único (slug) de la ley |
| `name` | string | Nombre oficial completo |
| `source_url` | string | URL de origen (diputados.gob.mx) |
| `pdf_url` | string | URL del PDF (puede ser null) |
| `scraped_at` | ISO 8601 | Fecha/hora del raspado |
| `html_checksum` | string | SHA-256 del HTML descargado |
| `html` | string | HTML completo de la página |

---

### `data/processed/<law_id>.json` — Ley estructurada

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | string | Identificador único (slug) |
| `name` | string | Nombre oficial completo |
| `short_name` | string | Acrónimo (ej. "LFT", "CFF") |
| `year_enacted` | integer | Año de publicación original |
| `year_last_reform` | integer | Año de la última reforma |
| `category` | string | Sector jurídico (ej. "fiscal", "trabajo") |
| `source_url` | string | URL de origen |
| `full_text` | string | Texto completo limpio (sin HTML) |
| `articles` | array | Lista de artículos (ver sub-esquema) |
| `num_articles` | integer | Número total de artículos |
| `char_count` | integer | Longitud del texto completo |
| `processed_at` | ISO 8601 | Fecha/hora del procesamiento |
| `scrape_checksum` | string | Checksum del HTML de origen |

**Sub-esquema `articles[]`:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `number` | string | Número del artículo (ej. "123", "1-A") |
| `title` | string | Encabezado del artículo |
| `text` | string | Texto completo del artículo |

---

### `data/citations/<law_id>_citations.json` — Citas extraídas

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `law_id` | string | ID de la ley fuente |
| `extracted_at` | ISO 8601 | Fecha/hora de la extracción |
| `total_citations` | integer | Total de citas en este archivo |
| `citations` | array | Lista de citas (ver sub-esquema) |

**Sub-esquema `citations[]`:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `source_law` | string | ID de la ley que contiene la cita |
| `source_article` | string | Número del artículo fuente |
| `target_law_raw` | string | Nombre de la ley referenciada tal como aparece en el texto |
| `target_law_id` | string/null | ID canónico resuelto (null si no resuelto) |
| `target_article` | string/null | Artículo referenciado, si se especifica |
| `citation_text` | string | Fragmento de texto con contexto (±150 chars) |
| `pattern_name` | string | Nombre del patrón de regex que hizo match |
| `pattern_group` | string | Grupo del patrón: "primary", "secondary", "constitutional" |
| `confidence` | string | "high", "medium" o "low" |
| `char_offset` | integer | Posición del match en el texto del artículo |
| `target_law_id` | string/null | Resuelto en paso 04 |
| `resolution_confidence` | string | Confianza de la resolución |
| `resolution_score` | float | Score de similitud (0-1) |
| `resolution_matched_alias` | string | Alias que hizo match |

---

### `data/definitions/<law_id>_definitions.json` — Definiciones

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `law_id` | string | ID de la ley |
| `extracted_at` | ISO 8601 | Fecha/hora |
| `total_definitions` | integer | Número de definiciones extraídas |
| `definitions` | array | Lista de definiciones |

**Sub-esquema `definitions[]`:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `law_id` | string | ID de la ley |
| `law_name` | string | Nombre completo de la ley |
| `article` | string | Número del artículo donde aparece |
| `term` | string | Término definido (normalizado a minúsculas) |
| `definition_text` | string | Texto de la definición (máx 500 chars) |
| `extraction_method` | string | Método usado: "definition_block", "se_entiende", "se_considera" |

---

### `data/graph/graph.json` — Grafo para visualización

```json
{
  "nodes": [
    {
      "id": "ley-federal-del-trabajo",
      "name": "Ley Federal del Trabajo",
      "short": "LFT",
      "sector": "trabajo",
      "in_degree": 42,
      "out_degree": 15,
      "pagerank": 0.0312,
      "betweenness": 0.0045,
      "community": 2,
      "cascade_score": 38,
      "url": "https://..."
    }
  ],
  "links": [
    {
      "source": "ley-isr",
      "target": "codigo-fiscal-federacion",
      "confidence": "high",
      "citation_count": 45,
      "sample_article": "14, 18, 90"
    }
  ]
}
```

---

### `data/graph/diagnostics.json` — Diagnósticos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `generated_at` | ISO 8601 | Fecha/hora de generación |
| `graph_stats` | object | Estadísticas básicas del grafo |
| `orphan_references` | array | Referencias a leyes abrogadas/desconocidas |
| `hub_laws` | array | Top 20 leyes por PageRank |
| `isolated_laws` | array | Leyes con grado total ≤ 2 |
| `cascade_analysis` | array | Análisis de impacto por ley |
| `circular_dependencies` | array | Ciclos detectados |
| `community_analysis` | array | Descripción de cada comunidad |
| `definition_conflicts` | array | Términos con definiciones conflictivas |

---

## Tabla de identidades canónicas (`scripts/utils/lookup.py`)

| Campo | Descripción |
|-------|-------------|
| `name` | Nombre oficial completo |
| `short` | Acrónimo o abreviatura oficial |
| `aliases` | Lista de nombres alternativos conocidos |
| `sector` | Sector jurídico |
| `url` | URL del PDF en diputados.gob.mx |

---

## Convenciones de identificadores

Los IDs de leyes son slugs en minúsculas con guiones:

- Solo caracteres ASCII: `a-z`, `0-9`, `-`
- Sin acentos ni caracteres especiales
- Ejemplos:
  - `ley-federal-del-trabajo`
  - `codigo-fiscal-federacion`
  - `lgeepa`
  - `constitucion-politica`

El ID especial `unresolved` se usa para citas que no pudieron mapearse a ninguna ley conocida.
