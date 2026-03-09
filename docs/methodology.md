# Metodología — Genoma Regulatorio de México

## Resumen

Este documento describe el proceso técnico para construir la red de citación del corpus jurídico federal mexicano. El pipeline consta de siete pasos secuenciales, cada uno implementado como un script de Python independiente.

---

## Paso 1: Raspado del corpus (`01_scrape.py`)

### Fuente primaria

La fuente principal es el [portal de la Cámara de Diputados](https://www.diputados.gob.mx/LeyesBiblio/index.htm), que publica el texto íntegro de todas las leyes federales vigentes en formato HTML.

### Protocolo de raspado

- **Identificación**: El agente de usuario identifica el proyecto y proporciona información de contacto.
- **Velocidad**: 1.5 segundos de espera entre solicitudes para no sobrecargar el servidor.
- **Idempotencia**: Cada archivo se verifica mediante checksum SHA-256. Solo se vuelven a descargar los archivos que han cambiado.
- **Resiliencia**: Hasta 3 reintentos con espera exponencial (2s, 4s, 8s) ante fallos de red.
- **Registro**: Cada éxito y fallo se registra en `data/scrape.log`.

### Formato de salida

Cada ley se guarda como `data/raw/<law_id>.json`:

```json
{
  "id": "ley-federal-del-trabajo",
  "name": "Ley Federal del Trabajo",
  "source_url": "https://www.diputados.gob.mx/LeyesBiblio/htm/LFT.htm",
  "scraped_at": "2024-01-15T10:30:00Z",
  "html_checksum": "sha256:abc123...",
  "html": "..."
}
```

---

## Paso 2: Análisis sintáctico (`02_parse.py`)

### Limpieza de HTML

Se utilizan reglas de extracción específicas para el formato de diputados.gob.mx:

1. Eliminación de scripts, estilos, navegación y elementos no textuales.
2. Extracción del contenido de cada elemento de bloque (`<p>`, `<td>`, `<div>`, etc.).
3. Normalización de espacios en blanco.

### Segmentación en artículos

Los artículos se detectan mediante expresiones regulares que reconocen los encabezados estándar del derecho mexicano:

- `Artículo 1.`
- `ARTÍCULO 1`
- `Art. 1.-`

Cada artículo se almacena como un objeto `{number, title, text}` en el arreglo `articles[]`.

### Extracción de metadatos

- **Año de publicación**: Buscado en el encabezado del texto con el patrón `publicada en el D.O.F. [fecha]`.
- **Año de última reforma**: Extraído del aviso `Última reforma publicada [fecha]`.
- **Nombre corto/acrónimo**: Tomado de la tabla de referencia canónica (`scripts/utils/lookup.py`).

---

## Paso 3: Extracción de citas (`03_extract_citations.py`)

### Estrategia

La cita jurídica mexicana sigue patrones formulaicos altamente estandarizados, derivados del estilo de redacción normativa de la Secretaría de Gobernación. Esto hace que las expresiones regulares sean efectivas para ~80% de las referencias.

### Patrones primarios (alta confianza)

| Patrón | Ejemplo |
|--------|---------|
| `conforme_dispuesto` | "conforme a lo dispuesto en la **Ley General de Salud**" |
| `terminos_establecido` | "en términos de lo establecido por la **LIC**" |
| `de_acuerdo` | "de acuerdo con el **Código Fiscal de la Federación**" |
| `lo_previsto` | "lo previsto en la **Ley de Amparo**" |
| `conformidad` | "de conformidad con la **LGEEPA**" |
| `en_los_terminos` | "en los términos de la **Ley del Trabajo**" |
| `a_que_refiere` | "a que se refiere la **Ley de Migración**" |
| `lo_dispuesto` | "lo dispuesto por la **Ley del Seguro Social**" |
| `prevista_en` | "prevista en la **Ley de Telecomunicaciones**" |
| `establecida_en` | "establecida en la **Ley Bancaria**" |
| `regulada_por` | "regulada por la **Ley Fintech**" |
| `senalada_en` | "señalada en la **Ley de Transparencia**" |
| `fundamento_articulo` | "con fundamento en el artículo 5 de la **Ley del IEPS**" |

### Referencias constitucionales

Las referencias a la Constitución tienen tratamiento especial:

- Se detectan mediante patrones específicos (nombre completo, `artículo N constitucional`).
- Siempre se resuelven al nodo `constitucion-politica`.
- Se extrae el número de artículo referenciado para análisis posterior.

### Registro de cada cita

```json
{
  "source_law": "ley-isr",
  "source_article": "14",
  "target_law_raw": "Código Fiscal de la Federación",
  "target_law_id": null,
  "target_article": "5",
  "citation_text": "...conforme a lo dispuesto en el Código Fiscal...",
  "pattern_name": "conforme_dispuesto",
  "confidence": "high",
  "char_offset": 2453
}
```

---

## Paso 4: Resolución de entidades (`04_resolve_entities.py`)

### El problema

Una misma ley puede ser referenciada por múltiples nombres:

- Nombre completo: "Ley Federal del Trabajo"
- Abreviado: "Ley del Trabajo"
- Acrónimo: "LFT"
- Informal: "la ley laboral"

### Algoritmo de resolución (cascada)

1. **Coincidencia exacta**: Búsqueda directa en la tabla de alias.
2. **Coincidencia de acrónimo**: Verificación si la cadena es un acrónimo conocido (2-8 letras mayúsculas).
3. **Coincidencia difusa**: `difflib.SequenceMatcher` con umbral ≥ 0.75.
4. **Coincidencia parcial**: Los primeros 15 caracteres de la cadena contra los alias.
5. **No resuelto**: Se marca como `"unresolved"` para revisión manual.

### Registro de resoluciones

Cada resolución registra:
- El alias que hizo match
- El score de similitud (0-1)
- El nivel de confianza resultante

Las citas no resueltas se exportan a `data/lookup/unresolved.json` para revisión manual.

---

## Paso 5: Extracción de definiciones (`05_extract_definitions.py`)

### Objetivo

Extraer los términos definidos formalmente en cada ley para:
1. Detectar conflictos (mismo término, diferentes definiciones).
2. Construir un glosario jurídico comparado.
3. Apoyar el análisis de coherencia normativa.

### Patrones detectados

- `Para los efectos de esta Ley, se entiende por:`
- `Se considerará [término] a...`
- Listas numeradas o con numeración romana en artículos de definiciones.

---

## Paso 6: Construcción del grafo (`06_build_graph.py`)

### Estructura

- **Nodos**: Leyes federales (con sus metadatos como atributos).
- **Aristas**: Citations agregadas. Si la Ley A cita a la Ley B en 10 artículos, existe una única arista dirigida A→B con peso 10.
- **Filtro de confianza**: Solo se incluyen citas con confianza ≥ `medium` por defecto.

### Métricas computadas

| Métrica | Descripción |
|---------|-------------|
| **in_degree** | Número de leyes que citan a esta ley |
| **out_degree** | Número de leyes que esta ley cita |
| **PageRank** | Importancia estructural (leyes citadas por leyes importantes) |
| **Betweenness** | Papel de "puente" o intermediario en la red |
| **Hub score** | Ley que cita a muchas autoridades (HITS) |
| **Authority score** | Ley citada por muchos hubs (HITS) |
| **Community** | Cluster detectado por Louvain |
| **Cascade score** | Leyes afectadas si esta ley se reforma |

### Formatos de salida

- `graph.graphml`: Para análisis en NetworkX o Gephi.
- `graph.json`: Para la visualización D3.js (formato `{nodes, links}`).
- `metrics.json`: Métricas por nodo y resumen del grafo.

---

## Paso 7: Diagnósticos (`07_diagnostics.py`)

| Diagnóstico | Descripción |
|-------------|-------------|
| **Referencias huérfanas** | Citas a leyes abrogadas o no identificadas |
| **Leyes más centrales** | Top 20 por PageRank — las "columnas vertebrales" del sistema |
| **Leyes aisladas** | Leyes con grado total ≤ 2 — posiblemente obsoletas |
| **Análisis de cascada** | Impacto potencial de reformar cada ley |
| **Dependencias circulares** | Ciclos A→B→A en la red |
| **Conflictos de definición** | Mismo término, diferentes definiciones |
| **Análisis de comunidades** | Sectores regulatorios detectados automáticamente |

---

## Limitaciones conocidas

1. **Cobertura de patrones**: Los patrones de regex capturan ~80% de las citas formulaicas. Las referencias informales o implícitas no se detectan.

2. **Ambigüedad de nombres**: Leyes que comparten palabras en su nombre pueden generar falsas coincidencias en la resolución difusa.

3. **Leyes abrogadas**: La tabla de leyes abrogadas (`ABROGATED_LAWS` en `07_diagnostics.py`) es incompleta y requiere actualización manual.

4. **Dinámicas temporales**: Las reformas constitucionales de 2024 (reforma judicial, eliminación de organismos autónomos) modificaron el corpus. El análisis está anclado a la fecha del raspado.

5. **Scope federal**: Solo se mapean referencias ley federal → ley federal. Se omiten tratados internacionales, leyes estatales y reglamentos.

---

*Este documento se actualiza con cada versión mayor del pipeline.*
