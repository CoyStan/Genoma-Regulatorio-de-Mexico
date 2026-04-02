# Genoma Regulatorio de México 🇲🇽

Una red de citación interactiva de todo el corpus jurídico federal mexicano.

Cada ley federal es un nodo. Cada referencia cruzada entre leyes es una arista dirigida.
El resultado es un mapa navegable de la estructura del derecho mexicano.

**👉 [Ver dashboard 3D en vivo](https://coystan.github.io/Genoma-Regulatorio-de-Mexico)**

---

## ¿Por qué?

México tiene ~318 leyes federales vigentes que se referencian entre sí miles de veces.
Nadie ha visualizado esta red completa. Sin ver la estructura, es imposible reformarla
con coherencia.

Este proyecto construye la infraestructura para responder preguntas como:

- ¿Qué leyes son las "columnas vertebrales" del sistema jurídico?
- ¿Qué leyes contienen referencias a leyes ya abrogadas?
- ¿Qué sectores regulatorios están más interconectados?
- Si se reforma la Ley X, ¿cuántas otras leyes se verían afectadas?
- ¿Dónde hay conflictos entre definiciones de leyes del mismo sector?
- ¿Qué leyes podrían abrogarse o fusionarse sin romper el sistema?

---

## Resultados

| Métrica | Valor |
|---------|-------|
| Leyes analizadas | 318 |
| Citas extraídas | 10,844 |
| Conexiones en la red | 4,497 |
| Comunidades regulatorias | 6 |
| Dependencias circulares (pares) | 599 |
| Candidatas a abrogación (score ≥ 80) | 160 (50% del corpus) |
| Pares candidatos a fusión | 40 |
| Términos con definición conflictiva | 50 |

Ver análisis completo en [`RESULTADOS.md`](RESULTADOS.md).

---

## Estructura del repositorio

```
genoma-regulatorio/
├── data/
│   ├── raw/                    # HTML/DOC raspado de cada ley
│   ├── processed/              # Leyes limpias con artículos indexados
│   ├── citations/              # Citas extraídas por ley (_citations.json)
│   ├── definitions/            # Definiciones extraídas (_definitions.json)
│   ├── graph/
│   │   ├── graph.json          # Red completa (D3-compatible)
│   │   ├── graph.graphml       # Red en formato GraphML
│   │   ├── metrics.json        # PageRank, betweenness, cascada por ley
│   │   ├── diagnostics.json    # Diagnósticos estructurales
│   │   ├── article_graph.json  # Red a nivel artículo (para dashboard 3D)
│   │   ├── simplification.json # Candidatas a abrogación/fusión/reforma
│   │   ├── cycles_dataset.csv  # 262 pares cíclicos con texto literal
│   │   └── cycles_dataset.json # Ídem en JSON
│   └── lookup/                 # Tablas de resolución de entidades
├── scripts/
│   ├── 01_scrape.py            # Raspado del corpus (diputados.gob.mx)
│   ├── 02_parse.py             # Limpieza y estructuración de artículos
│   ├── 03_extract_citations.py # Extracción de citas por regex
│   ├── 04_resolve_entities.py  # Resolución de nombres a IDs canónicos
│   ├── 05_extract_definitions.py # Extracción de definiciones legales
│   ├── 06_build_graph.py       # Construcción de la red + métricas NetworkX
│   ├── 07_diagnostics.py       # Diagnósticos estructurales
│   ├── 09_article_stats.py     # Estadísticas por artículo para dashboard
│   ├── 10_build_article_graph.py # Red 3D a nivel artículo
│   ├── 11_simplification_report.py # Análisis de simplificación regulatoria
│   ├── 12_generate_charts.py   # Gráficas para Twitter/publicaciones
│   ├── 13_export_cycles.py     # Dataset de ciclos con texto literal
│   └── utils/
│       ├── patterns.py         # 19 regex de citas jurídicas
│       ├── lookup.py           # Tabla canónica de 318 leyes + aliases
│       └── metrics.py          # Métricas de red (PageRank, HITS, Louvain)
├── docs/                       # GitHub Pages — dashboard en vivo
│   ├── index.html              # Visualizador 3D (Three.js + 3d-force-graph)
│   ├── graph.js                # Lógica del grafo 3D
│   ├── articles.js             # Tab de análisis por artículo
│   ├── style.css
│   ├── assets/charts/          # Gráficas PNG para publicaciones
│   └── thread_twitter.md       # Borrador del hilo de Twitter
├── tests/
│   ├── test_patterns.py        # ~35 casos de prueba con texto real
│   └── test_resolution.py      # Tests de resolución de entidades
├── RESULTADOS.md               # Hallazgos principales en español
└── CLAUDE.md                   # Guía para Claude Code
```

---

## Instalación

```bash
git clone https://github.com/CoyStan/Genoma-Regulatorio-de-Mexico
cd Genoma-Regulatorio-de-Mexico
pip install -r requirements.txt
```

---

## Pipeline completo

```bash
# ETL principal
python scripts/01_scrape.py              # Raspar corpus (~30-60 min)
python scripts/02_parse.py              # Estructurar artículos
python scripts/03_extract_citations.py  # Extraer citas (regex)
python scripts/04_resolve_entities.py   # Resolver nombres → IDs
python scripts/05_extract_definitions.py # Extraer definiciones (opcional)
python scripts/06_build_graph.py        # Construir red + métricas
python scripts/07_diagnostics.py        # Diagnósticos estructurales

# Análisis adicionales
python scripts/09_article_stats.py      # Estadísticas para tab de artículos
python scripts/10_build_article_graph.py # Red 3D a nivel artículo
python scripts/11_simplification_report.py # Reporte de simplificación
python scripts/12_generate_charts.py    # Gráficas PNG
python scripts/13_export_cycles.py      # Dataset de ciclos con texto
```

---

## Dashboard

El dashboard 3D está disponible en:
**[coystan.github.io/Genoma-Regulatorio-de-Mexico](https://coystan.github.io/Genoma-Regulatorio-de-Mexico)**

Incluye:
- **Tab Grafo**: red 3D navegable, resaltado por ley, filtros de rendimiento
- **Tab Artículos**: top 100 artículos más citados + drilldown por ley

Para correr localmente:
```bash
cd docs && python -m http.server 8080
# Abrir http://localhost:8080
```

---

## Tests

```bash
python -m pytest tests/ -v
```

Cubre extracción de citas (~35 casos reales), resolución de entidades e integridad de la tabla canónica.

---

## Stack tecnológico

| Componente | Tecnología |
|------------|-----------|
| Scraping | `requests` + `BeautifulSoup4` |
| Análisis de texto | `re` (regex), `difflib` |
| Análisis de red | `NetworkX` + `python-louvain` |
| Visualización estática | `matplotlib` |
| Dashboard 3D | `Three.js` + `3d-force-graph` |
| Despliegue | GitHub Pages |
| Almacenamiento | JSON |

---

## Datos

- **Fuente primaria**: [Cámara de Diputados — Leyes Federales](https://www.diputados.gob.mx/LeyesBiblio/index.htm)
- **Fecha del corpus**: Documentada en `data/scrape.log`

---

## Advertencia legal

> Este proyecto es un ejercicio de análisis estructural del marco jurídico mexicano.
> **No constituye asesoría legal.**
> Los datos provienen de fuentes públicas y pueden contener errores de extracción.
> La fuente oficial de la legislación federal es el
> [Diario Oficial de la Federación](https://www.dof.gob.mx).

---

## Autor

[Quetzali Ramírez Guillén](https://twitter.com/QuetzalRG)
CIDE · Harvard MPA/ID · IMF

_Las opiniones expresadas son personales y no representan la posición del FMI._

---

## Licencia

MIT — ver [LICENSE](LICENSE)
