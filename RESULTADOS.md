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
| Conexiones (citas entre leyes) | 4,074 |
| Densidad de la red | 0.031 |
| Comunidades regulatorias detectadas | 7 |
| Dependencias circulares (citas mutuas) | 96 |
| Referencias huérfanas | 1,013 |
| Leyes aisladas | 27 |

### Las 10 leyes más centrales (por PageRank)

Estas leyes son las más referenciadas — reformarlas tendría el mayor impacto en cascada sobre el resto del sistema:

1. **Constitución Política (CPEUM)** — citada por 316 de 318 leyes. Afecta en cascada a 317 leyes.
2. **Ley Federal de Competencia Económica (LFCE)** — citada por 220 leyes, impacto en cascada: 230 leyes
3. **Ley General de Sociedades Mercantiles (LGSM)** — citada por 205 leyes, impacto en cascada: 230 leyes
4. **Ley de Petróleos Mexicanos (LPEMEX)** — citada por 169 leyes, impacto en cascada: 205 leyes
5. **Ley Orgánica de la Administración Pública Federal (LOAPF)** — citada por 119 leyes, impacto en cascada: 177 leyes
6. **Ley General de Educación (LGE)** — citada por 109 leyes, impacto en cascada: 169 leyes
7. **Ley Federal de Procedimiento Administrativo (LFPA)** — citada por 94 leyes, impacto en cascada: 111 leyes
8. **Código Nacional de Procedimientos Penales (CNPP)** — citada por 103 leyes, impacto en cascada: 108 leyes
9. **Ley Federal del Trabajo (LFT)** — citada por 97 leyes, impacto en cascada: 121 leyes
10. **Ley Federal de Telecomunicaciones y Radiodifusión (LFTR)** — citada por 83 leyes, impacto en cascada: 158 leyes

### 7 Comunidades Regulatorias

| Comunidad | Leyes | Ley Central |
|-----------|-------|-------------|
| Constitucional / General | 87 | Constitución Política (CPEUM) |
| Competencia / Mercantil | 76 | Ley Federal de Competencia Económica |
| Societario / Mercantil | 73 | Ley General de Sociedades Mercantiles |
| Energía | 50 | Ley de Petróleos Mexicanos |
| Financiero | 33 | Ley de Instituciones de Crédito |
| Penal | 23 | Código Nacional de Procedimientos Penales |
| Fiscal | 18 | Ley del Impuesto sobre la Renta |

### 96 Dependencias Circulares

Pares de leyes que se citan mutuamente. Ejemplos notables:
- **Ley Federal del Trabajo ↔ Ley del Seguro Social**
- **Ley de Instituciones de Crédito ↔ Ley del Mercado de Valores**

### 27 Leyes Aisladas

Leyes con 2 o menos conexiones: Ley de Capitalización del PROCAMPO, Ley de Recompensas de la Armada, Ley para Conservar la Neutralidad del País, entre otras.

### 50 Conflictos de Definición

Términos definidos de forma distinta en múltiples leyes:
- **"secretaría"** — definido en 11 leyes distintas
- **"ley"** — definido en 11 leyes distintas
- **"comisión"** — definido en 10 leyes distintas
- **"consejo"** — definido en 8 leyes distintas

---

## Limitaciones Actuales

- El **85.7% de las citas fueron resueltas** — el 14.3% restante incluye referencias genéricas ("ley de la materia", "Reglamento de esta Ley") y leyes abrogadas
- La alta centralidad de LFCE y LPEMEX puede incluir artefactos del patrón `direct_mention` — requiere verificación adicional
- La extracción de citas es por patrones de texto (regex), no NLP — puede perder referencias complejas
- El análisis es **estático** — no captura la evolución histórica de las reformas

---

## Próximos Pasos Sugeridos

1. Investigar las 1,013 referencias huérfanas (nodos citados que no están en el corpus)
2. Verificar manualmente una muestra de las 96 dependencias circulares
3. Mejorar la clasificación de sectores para las comunidades etiquetadas como "unknown"
4. Análisis temporal: incorporar fechas de reforma para ver cómo evoluciona la red

---

_Datos: diputados.gob.mx | Código: github.com/CoyStan/Genoma-Regulatorio-de-Mexico_
