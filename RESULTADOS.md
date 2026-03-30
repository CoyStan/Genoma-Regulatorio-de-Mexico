# Genoma Regulatorio de México — Resultados Preliminares

_Análisis con 87 de ~296 leyes federales (84 archivos aún pendientes de descarga)_

---

## ¿Qué se hizo?

Se construyó una red de citaciones del corpus jurídico federal mexicano. Cada ley es un nodo; cada vez que una ley menciona a otra, se crea una arista. Se analizó la red tanto a nivel de **ley** como a nivel de **artículo individual**.

---

## Red a Nivel de Ley

| Métrica | Valor |
|---------|-------|
| Leyes analizadas | 87 |
| Nodos en la red | 135 (incluye leyes citadas no descargadas) |
| Conexiones (citas entre leyes) | 848 |
| Comunidades regulatorias detectadas | 8 |
| Dependencias circulares | 0 |
| Referencias huérfanas | 0 |

### Las 10 leyes más centrales (por PageRank)

Estas leyes son las más referenciadas — reformarlas tendría el mayor impacto en cascada sobre el resto del sistema:

1. **Constitución Política (CPEUM)** — citada por 86 de 87 leyes. Afecta en cascada a todo el corpus.
2. **Ley Federal de Competencia Económica** — citada por 59 leyes
3. **Ley de Petróleos Mexicanos** — citada por 50 leyes
4. **Ley General de Sociedades Mercantiles** — citada por 47 leyes
5. **Ley Orgánica de la Administración Pública Federal** — citada por 32 leyes
6. **Código Nacional de Procedimientos Penales** — citada por 31 leyes
7. **Ley Federal del Trabajo** — citada por 26 leyes
8. **Ley General de Salud** — citada por 24 leyes
9. **Ley Federal de Procedimiento Administrativo** — citada por 22 leyes
10. **Ley Federal de Telecomunicaciones y Radiodifusión** — citada por 23 leyes

### 8 Comunidades Regulatorias

| Comunidad | Leyes | Ley Central |
|-----------|-------|-------------|
| Competencia / Mercantil | 40 | Ley Federal de Competencia Económica |
| Constitucional / General | 36 | Constitución |
| Energía | 18 | Ley de Petróleos Mexicanos |
| Financiero / Mercantil | 16 | Ley General de Sociedades Mercantiles |
| Fiscal | 10 | Código Fiscal de la Federación |
| Penal | 9 | Código Nacional de Procedimientos Penales |
| Propiedad Intelectual | 5 | Ley Federal del Derecho de Autor |
| Presupuesto | 1 | Presupuesto de Egresos 2025 |

### 13 Leyes Aisladas (posiblemente obsoletas o muy especializadas)

Leyes con 2 o menos conexiones al resto de la red: Ley de Amnistía, Ley de Educación Naval, Ley de Juegos y Sorteos, entre otras.

### 6 Conflictos de Definición

Términos definidos de forma distinta en múltiples leyes:
- **"comisión"** — definido en 3 leyes distintas
- **"fondo"**, **"ley"**, **"ajustes razonables"**, **"constitución"**, **"cuenca hidrológica"** — definidos en 2 leyes cada uno

---

## Red a Nivel de Artículo

| Métrica | Valor |
|---------|-------|
| Artículos únicos (nodos) | 1,382 |
| Conexiones entre artículos | 2,087 |
| Artículos que citan otras leyes | 1,224 |
| Artículos citados por nombre específico | 110 |

### Artículos constitucionales más citados

El **Artículo 89** (facultades del Ejecutivo) es el más citado del sistema: 77 veces desde 70 leyes distintas. Le siguen el **Art. 123** (trabajo, 22 veces) y el **Art. 27** (propiedad y territorio, 19 veces).

### Artículos más complejos (más citas salientes)

| Artículo | Ley | Citas | Leyes distintas |
|----------|-----|-------|-----------------|
| Art. 56 | LOAPF | 49 | 17 |
| Art. 112 | Ley Electoral (LGSMIME) | 33 | 13 |
| Art. 76 | CNDH | 33 | 17 |
| Art. 118 | Presupuesto y Responsabilidad Hacendaria | 32 | 17 |
| Art. 45 | LOAPF | 28 | 19 |

### Leyes más complejas (total de referencias salientes)

| Ley | Referencias salientes |
|-----|----------------------|
| Código Fiscal de la Federación | 143 |
| Estatuto de Gobierno del Distrito Federal | 67 |
| Ley de Fiscalización y Rendición de Cuentas | 65 |
| Ley Federal de Presupuesto y Resp. Hacendaria | 62 |
| Ley Orgánica de la Admin. Pública Federal | 62 |

---

## Limitaciones Actuales

- Solo se procesaron **87 de ~296 leyes** — faltan 84 archivos `.doc` por descargar (ver `data/missing_docs.txt`)
- El **70.5% de las citas fueron resueltas** — el 29.5% restante no pudo mapearse a una ley conocida
- La extracción de citas es por patrones de texto (regex), no NLP — puede perder referencias complejas o anidadas
- El análisis es **estático** — no captura la evolución histórica de las reformas

---

## Próximos Pasos Sugeridos

1. Descargar los 84 archivos `.doc` faltantes y re-correr el pipeline completo
2. Mejorar la resolución de entidades (actualmente 70.5%) para reducir citas sin resolver
3. Explorar la red con las 296 leyes completas para validar las comunidades detectadas
4. Análisis temporal: incorporar fechas de reforma para ver cómo evoluciona la red

---

_Datos: diputados.gob.mx | Código: github.com/CoyStan/Genoma-Regulatorio-de-Mexico_
