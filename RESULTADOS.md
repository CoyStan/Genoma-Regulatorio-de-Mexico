# Genoma Regulatorio de México — Resultados Preliminares

_Análisis con 318 leyes federales procesadas (corpus casi completo)_

---

## ¿Qué se hizo?

Se construyó una red de citaciones del corpus jurídico federal mexicano. Cada ley es un nodo; cada vez que una ley menciona a otra, se crea una arista. Se analizó la red tanto a nivel de **ley** como a nivel de **artículo individual**.

---

## Red a Nivel de Ley

| Métrica | Valor |
|---------|-------|
| Leyes analizadas | 318 |
| Nodos en la red | 361 (incluye leyes citadas no descargadas) |
| Conexiones (citas entre leyes) | 4,534 |
| Densidad de la red | 0.035 |
| Comunidades regulatorias detectadas | 7 |
| Dependencias circulares (citas mutuas) | 195 |
| Leyes aisladas | 25 |

### Las 10 leyes más centrales (por PageRank)

Estas leyes son las más referenciadas — reformarlas tendría el mayor impacto en cascada sobre el resto del sistema:

1. **Constitución Política (CPEUM)** — citada por 316 de 318 leyes. Afecta en cascada a 317 leyes.
2. **Ley General de Sociedades Mercantiles (LGSM)** — citada por 203 leyes, impacto en cascada: 269 leyes
3. **Ley Orgánica del Poder Judicial de la Federación (LOPJF)** — citada por 138 leyes, impacto en cascada: 262 leyes
4. **Ley Federal de Competencia Económica (LFCE)** — citada por 144 leyes, impacto en cascada: 266 leyes
5. **Ley General de Educación (LGE)** — citada por 107 leyes, impacto en cascada: 266 leyes
6. **Código Nacional de Procedimientos Penales (CNPP)** — citada por 102 leyes, impacto en cascada: 267 leyes
7. **Ley Orgánica de la Administración Pública Federal (LOAPF)** — citada por 91 leyes, impacto en cascada: 259 leyes
8. **Ley Federal de Procedimiento Administrativo (LFPA)** — citada por 91 leyes, impacto en cascada: 267 leyes
9. **Ley Federal del Trabajo (LFT)** — citada por 93 leyes, impacto en cascada: 257 leyes
10. **Ley General de Instituciones y Procedimientos Electorales (LGIPE)** — citada por 82 leyes, impacto en cascada: 263 leyes

### 7 Comunidades Regulatorias

| Comunidad | Leyes | Ley Central |
|-----------|-------|-------------|
| Constitucional / General | 100 | Constitución Política (CPEUM) |
| Financiero / Mercantil | 64 | Ley General de Sociedades Mercantiles |
| Competencia / Regulación | 63 | Ley Federal de Competencia Económica |
| Propiedad Intelectual / Cultural | 55 | Ley Federal del Derecho de Autor |
| Salud / Social | 39 | Ley General de Salud |
| Administrativo | 27 | Ley Orgánica de la Administración Pública Federal |
| Fiscal / Energía | 13 | Ley de Hidrocarburos |

### 195 Dependencias Circulares

Pares de leyes que se citan mutuamente. Ejemplos notables:
- **Ley Federal del Trabajo ↔ Ley del Seguro Social**
- **Ley de Instituciones de Crédito ↔ Ley del Mercado de Valores**

### 25 Leyes Aisladas

Leyes con 2 o menos conexiones: Ley de Capitalización del PROCAMPO, Ley de Recompensas de la Armada, Ley para Conservar la Neutralidad del País, entre otras.

### 50 Conflictos de Definición

Términos definidos de forma distinta en múltiples leyes:
- **"secretaría"** — definido en 11 leyes distintas
- **"ley"** — definido en 11 leyes distintas
- **"comisión"** — definido en 10 leyes distintas
- **"consejo"** — definido en 8 leyes distintas

---

## Limitaciones Actuales

- El **87.1% de las citas fueron resueltas** (10,844 de 12,444) — el 12.9% restante incluye referencias genéricas ("ley de la materia", "Reglamento de esta Ley") y leyes abrogadas
- La extracción de citas es por patrones de texto (regex), no NLP — puede perder referencias complejas
- El análisis es **estático** — no captura la evolución histórica de las reformas

---

## Correcciones Metodológicas Aplicadas

- **Falsos positivos `direct_mention`**: Se añadió filtro de contexto para excluir citas en listas de derogación, preámbulos de decretos y referencias genéricas
- **LPEMEX falso alias**: El alias "Ley Orgánica de PEMEX" atraía todas las "Ley Orgánica de X" — eliminado
- **LFCE falso partial match**: El mecanismo de coincidencia parcial en lookup.py mapeaba todas las "Ley Federal de X" a LFCE — corregido priorizando el registro de corpus sobre coincidencias de baja confianza
- **Registro de corpus dinámico**: Resolución ampliada de 48 leyes hardcodeadas a las 318 del corpus completo

---

## Próximos Pasos Sugeridos

1. Mejorar la clasificación de sectores para las comunidades etiquetadas como "unknown"
2. Investigar las ~1,580 referencias huérfanas (nodos citados que no están en el corpus)
3. Verificar manualmente una muestra de las 195 dependencias circulares
4. Análisis temporal: incorporar fechas de reforma para ver cómo evoluciona la red

---

_Datos: diputados.gob.mx | Código: github.com/CoyStan/Genoma-Regulatorio-de-Mexico_
