# Genoma Regulatorio de México 🇲🇽

Una red de citación interactiva de todo el corpus jurídico federal mexicano.

Cada ley federal es un nodo. Cada referencia cruzada entre leyes es una arista dirigida.
El resultado es un mapa navegable de la estructura del derecho mexicano.

---

## ¿Por qué?

México tiene ~296 leyes federales vigentes que se referencian entre sí miles de veces.
Nadie ha visualizado esta red completa. Sin ver la estructura, es imposible reformarla
con coherencia.

Este proyecto construye la infraestructura para responder preguntas como:

- ¿Qué leyes son las "columnas vertebrales" del sistema jurídico?
- ¿Qué leyes contienen referencias a leyes ya abrogadas?
- ¿Qué sectores regulatorios están más interconectados?
- Si se reforma la Ley X, ¿cuántas otras leyes se verían afectadas?
- ¿Dónde hay conflictos entre definiciones de leyes del mismo sector?

---

## Estructura del repositorio

```
genoma-regulatorio/
├── data/
│   ├── raw/                    # HTML raspado de cada ley
│   ├── processed/              # Leyes limpias con artículos indexados
│   ├── citations/              # Citas extraídas (por ley)
│   ├── definitions/            # Definiciones extraídas
│   ├── graph/                  # Red de citación (GraphML, JSON)
│   └── lookup/                 # Tablas de resolución de entidades
├── scripts/
│   ├── 01_scrape.py           # Raspado del corpus
│   ├── 02_parse.py            # Limpieza y estructuración
│   ├── 03_extract_citations.py # Extracción de citas
│   ├── 04_resolve_entities.py  # Resolución de nombres a IDs
│   ├── 05_extract_definitions.py # Extracción de definiciones
│   ├── 06_build_graph.py      # Construcción de la red
│   ├── 07_diagnostics.py      # Diagnósticos estructurales
│   └── utils/
│       ├── patterns.py         # Regex de citas jurídicas
│       ├── lookup.py           # Tabla canónica de leyes
│       └── metrics.py          # Métricas de red (NetworkX)
├── frontend/
│   ├── index.html             # Visualizador interactivo
│   ├── graph.js               # D3.js force-directed graph
│   └── style.css
├── tests/
│   ├── test_patterns.py       # Tests de extracción de citas
│   └── test_resolution.py     # Tests de resolución de entidades
└── docs/
    ├── methodology.md          # Metodología detallada
    ├── data_dictionary.md      # Esquema de datos
    └── limitations.md          # Limitaciones conocidas
```

---

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/quetzali-rg/genoma-regulatorio-mx
cd genoma-regulatorio-mx

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows

# Instalar dependencias
pip install -r requirements.txt
```

---

## Uso: Pipeline completo

```bash
# Paso 1: Raspar el corpus (tarda ~30-60 min, respeta delays)
python scripts/01_scrape.py

# Paso 2: Limpiar y estructurar los textos
python scripts/02_parse.py

# Paso 3: Extraer citas de cada ley
python scripts/03_extract_citations.py

# Paso 4: Resolver nombres a IDs canónicos
python scripts/04_resolve_entities.py

# Paso 5: Extraer definiciones (opcional pero recomendado)
python scripts/05_extract_definitions.py

# Paso 6: Construir el grafo y calcular métricas
python scripts/06_build_graph.py

# Paso 7: Ejecutar diagnósticos estructurales
python scripts/07_diagnostics.py
```

Después de correr el pipeline, abrir `frontend/index.html` en un navegador
(o servir con `python -m http.server` desde el directorio `frontend/`).

---

## Uso: Visualización de demostración

Si no quieres correr el pipeline completo, el visualizador incluye un **modo de
demostración** con datos de muestra de 20 leyes:

```bash
cd frontend
python -m http.server 8080
# Abrir http://localhost:8080 y hacer clic en "Cargar demostración"
```

---

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

Los tests cubren:
- Extracción de citas: ~35 casos de prueba con texto real
- Resolución de entidades: exacta, acrónimos, alias, fuzzy, no resolvibles
- Integridad de la tabla canónica de leyes

---

## Stack tecnológico

| Componente | Tecnología |
|------------|-----------|
| Scraping | `requests` + `BeautifulSoup4` |
| Análisis de texto | `re` (regex), `difflib` |
| Análisis de red | `NetworkX` |
| Detección de comunidades | `python-louvain` |
| Frontend | `D3.js v7` |
| Almacenamiento | JSON (SQLite en roadmap) |

---

## Resultados preliminares (muestra)

> _Requiere correr el pipeline completo para obtener resultados reales._

Con datos completos, el análisis revela:

- **Nodo más central**: La Constitución (in-degree altísimo — casi toda ley la referencia)
- **Leyes más citadas después de la Constitución**: CFF, LFT, LSS, LOAPF
- **Comunidades detectadas**: ~12-15 clusters sectoriales (fiscal, laboral, financiero, penal, ambiental, etc.)
- **Referencias huérfanas**: Citas a leyes abrogadas en reformas de 2024
- **Dependencias circulares**: Varios pares de leyes complementarias que se referencian mutuamente

---

## Diagnósticos estructurales incluidos

1. **Referencias huérfanas**: Citas a leyes abrogadas o inexistentes
2. **Leyes más centrales**: Top 20 por PageRank — las "columnas vertebrales"
3. **Leyes aisladas**: Nodos con muy pocas conexiones — posiblemente obsoletas
4. **Análisis de cascada**: ¿Cuántas leyes se verían afectadas por una reforma?
5. **Dependencias circulares**: Leyes que se referencian mutuamente (A→B→A)
6. **Conflictos de definición**: El mismo término definido de forma distinta
7. **Comunidades regulatorias**: Clusters de leyes densamente interconectadas

---

## Datos

- **Fuente primaria**: [Cámara de Diputados — Leyes Federales](https://www.diputados.gob.mx/LeyesBiblio/index.htm)
- **Fuente de respaldo**: [Justia México](https://mexico.justia.com/federales/)
- **Fecha del corpus**: Documentada en `data/scrape.log`

---

## Contribuciones

Las contribuciones son bienvenidas. Áreas prioritarias:

1. **Mejora de patrones de citas**: Patrones adicionales o correcciones a los existentes.
2. **Tabla de alias**: Agregar nombres alternativos para leyes no cubiertas.
3. **Leyes abrogadas**: Completar el listado en `07_diagnostics.py`.
4. **Frontend**: Mejoras a la visualización (filtros, animaciones, exportación).
5. **Validación**: Revisión manual de casos ambiguos en `data/lookup/unresolved.json`.

---

## Advertencia legal

> Este proyecto es un ejercicio de análisis estructural del marco jurídico mexicano.
> **No constituye asesoría legal.**
> Los datos provienen de fuentes públicas y pueden contener errores de extracción.
> La fuente oficial de la legislación federal es el
> [Diario Oficial de la Federación](https://www.dof.gob.mx).

---

## Autora

[Quetzali Ramírez Guillén](https://twitter.com/QuetzalRG)
CIDE · Harvard MPA/ID · IMF

_Las opiniones expresadas son personales y no representan la posición del FMI._

---

## Licencia

MIT — ver [LICENSE](LICENSE)
