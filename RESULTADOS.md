# Genoma Regulatorio de México — Resultados Preliminares

_Análisis con 318 de ~319 leyes federales procesadas (corpus casi completo)_

---

## ¿Qué se hizo?

Se construyó una red de citaciones del corpus jurídico federal mexicano. Cada ley es un nodo; cada vez que una ley menciona a otra, se crea una arista. Se analizó la red tanto a nivel de **ley** como a nivel de **artículo individual**.

---

## Red a Nivel de Ley

| Métrica | Valor |
|---------|-------|
| Leyes analizadas | 318 |
| Nodos en la red | 361 (incluye leyes citadas no descargadas) |
| Conexiones (citas entre leyes) | 3,244 |
| Densidad de la red | 0.025 |
| Comunidades regulatorias detectadas | 8 |
| Dependencias circulares | 1 |
| Referencias huérfanas | 0 |
| Leyes aisladas | 38 |

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

### 8 Comunidades Regulatorias

| Comunidad | Leyes | Ley Central |
|-----------|-------|-------------|
| Constitucional / General | 87 | Constitución Política (CPEUM) |
| Competencia / Mercantil | 76 | Ley Federal de Competencia Económica |
| Societario / Mercantil | 73 | Ley General de Sociedades Mercantiles |
| Energía | 50 | Ley de Petróleos Mexicanos |
| Financiero | 33 | Ley de Instituciones de Crédito |
| Penal | 23 | Código Nacional de Procedimientos Penales |
| Fiscal | 18 | Ley del Impuesto sobre la Renta |
| Importación/Exportación | 1 | Ley de los Impuestos Generales de Importación y Exportación |

### 1 Dependencia Circular

- **Ley Federal del Trabajo ↔ Ley del Seguro Social** — se referencian mutuamente.

### 38 Leyes Aisladas (posiblemente obsoletas o muy especializadas)

Leyes con 2 o menos conexiones al resto de la red, entre ellas: Ley de Capitalización del PROCAMPO, Ley de Recompensas de la Armada, Ley para Conservar la Neutralidad del País, Ley de Educación Naval, entre otras.

### 50 Conflictos de Definición

Términos definidos de forma distinta en múltiples leyes (muestra):
- **"secretaría"** — definido en 11 leyes distintas
- **"ley"** — definido en 11 leyes distintas
- **"comisión"** — definido en 10 leyes distintas
- **"consejo"** — definido en 8 leyes distintas
- **"dependencias"** y **"entidades"** — definidos en 6 leyes cada uno

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

- El **71.3% de las citas fueron resueltas** — el 28.7% restante no pudo mapearse a una ley conocida (incluye referencias genéricas como "Reglamento de esta Ley" y "ley de la materia")
- La extracción de citas es por patrones de texto (regex), no NLP — puede perder referencias complejas o anidadas
- El análisis es **estático** — no captura la evolución histórica de las reformas
- La alta centralidad de la LFCE y LPEMEX merece verificación manual — puede haber artefactos de los patrones regex

---

## Próximos Pasos Sugeridos

1. Verificar manualmente por qué la Ley Federal de Competencia Económica y Ley de PEMEX tienen centralidad tan alta
2. Mejorar la clasificación de sectores (5 de 8 comunidades etiquetadas como "unknown")
3. Mejorar la resolución de entidades (actualmente 71.3%) para reducir citas sin resolver
4. Análisis temporal: incorporar fechas de reforma para ver cómo evoluciona la red

---

_Datos: diputados.gob.mx | Código: github.com/CoyStan/Genoma-Regulatorio-de-Mexico_
