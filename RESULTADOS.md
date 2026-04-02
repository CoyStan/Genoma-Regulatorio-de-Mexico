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
| Nodos en la red | 318 (sin nodos fantasma) |
| Conexiones (citas entre leyes) | 2,469 |
| Densidad de la red | 0.025 |
| Comunidades regulatorias detectadas | 12 |
| Dependencias circulares (citas mutuas) | 204 |
| Leyes aisladas | 46 |
| Referencias huérfanas reales | 4 |

### Las 10 leyes más centrales (por PageRank)

Estas leyes son las más referenciadas — reformarlas tendría el mayor impacto en cascada sobre el resto del sistema:

1. **Constitución Política (CPEUM)** — citada por 260 de 318 leyes (PageRank: 0.2518)
2. **Ley Orgánica del Congreso General (LOCG)** — PageRank: 0.0798
3. **Ley General de Instituciones y Procedimientos Electorales (LGIPE)** — PageRank: 0.0514
4. **Ley Federal del Trabajo (LFT)** — citada por 54 leyes (PageRank: 0.0350)
5. **Ley del Seguro Social (LSS)** — PageRank: 0.0288
6. **Ley del Impuesto sobre la Renta (LISR)** — citada por 47 leyes (PageRank: 0.0248)
7. **Ley del ISSSTE** — PageRank: 0.0200
8. **Ley General de Sociedades Mercantiles (LGSM)** — citada por 99 leyes (PageRank: 0.0191)
9. **Ley Nacional del Registro de Detenciones (LNRD)** — PageRank: 0.0186
10. **Ley Federal de Competencia Económica (LFCE)** — citada por 105 leyes (PageRank: 0.0176)

### 12 Comunidades Regulatorias

La red detecta 12 comunidades con la corrección de artículos transitorios (que inflan artificialmente la conectividad entre leyes). Las comunidades reflejan con mayor fidelidad la estructura real del sistema jurídico.

> _Nota: El aumento de 6 a 12 comunidades se explica por la exclusión de artículos transitorios del análisis. Los transitorios concentraban citas de derogación y reforma que creaban conexiones artificiales entre sectores. Sin ellos, la red es más dispersa pero más precisa._

### 204 Dependencias Circulares

Pares de leyes que se citan mutuamente en su texto sustantivo (excluidos artículos transitorios). Ejemplos notables:
- **Código Civil Federal ↔ Código Federal de Procedimientos Civiles**
- **Código Fiscal de la Federación ↔ Ley Aduanera**
- **Código Fiscal de la Federación ↔ Ley del Impuesto sobre la Renta**

### 46 Leyes Aisladas

Leyes con pocas o ninguna conexión en su texto sustantivo: Ley de Capitalización del PROCAMPO, Ley de Recompensas de la Armada, Ley para Conservar la Neutralidad del País, entre otras.

### 54 Conflictos de Definición

Términos definidos de forma distinta en múltiples leyes:
- **"secretaría"** — definido en 11 leyes distintas
- **"ley"** — definido en 11 leyes distintas
- **"comisión"** — definido en 10 leyes distintas
- **"consejo"** — definido en 8 leyes distintas

---

## Análisis de Simplificación Regulatoria

Basado en la red de citas, se cuantificó el potencial de reducir la complejidad del sistema legal federal.

| Métrica | Valor |
|---------|-------|
| Leyes candidatas a abrogación (score ≥ 80) | 121 (38% del corpus) |
| Leyes completamente aisladas (0 conexiones relevantes) | 37 |
| Pares candidatos a fusión (citan mutuamente, mismo sector) | 40 |
| Leyes que requieren reforma urgente (alta ambigüedad + ciclos) | 40 |

> _Nota: El análisis excluye artículos transitorios del cómputo de citas. Los transitorios concentran citas de derogación y reforma que no reflejan dependencias funcionales entre leyes. El 38% corresponde a leyes con baja integración estructural en su texto sustantivo — no a leyes sin utilidad jurídica._

### Candidatas a Abrogación

El **score de seguridad** (0–100) pondera: baja dependencia entrante (50%), bajo impacto en cascada (35%) y ausencia de ciclos (15%). Las 23 leyes completamente aisladas incluyen:

- **Ley para Conservar la Neutralidad del País** — ninguna ley la cita; cita solo 1
- **Ley de Recompensas de la Armada de México** — 0 dependencias, cita 2 leyes
- **Ley de Capitalización del PROCAMPO** — sin dependencias circulares, impacto mínimo
- **Ley de Responsabilidad Civil por Daños Nucleares** — citada por 0 leyes

### Pares Candidatos a Fusión

| Par | Sector | Score |
|-----|--------|-------|
| Ley Nacional de Competencia Mercantil ↔ Ley de Puertos y Uso Especial | mercantil | 88.3 |
| Ley de Disciplina Financiera de EF y M ↔ Ley General de Deuda Pública | fiscal | 88.0 |
| Ley de Amnistía ↔ Ley Nacional del Registro de Detenciones | penal | 75+ |

### Leyes que Requieren Reforma (no abrogación)

Leyes muy referenciadas con alta ambigüedad — eliminarlas rompería el sistema, pero concentran conflictos de definición y dependencias circulares:

1. **LFFAOSC** (Ley Federal de Fomento a Organizaciones de la Sociedad Civil) — score 375
2. **LCNBV** (Ley de la Comisión Nacional Bancaria y de Valores) — score 361
3. **CPEUM** — involucrada en el mayor número de dependencias circulares por volumen

---

## Limitaciones Actuales

- El **84.8% de las citas fueron resueltas** (6,249 de 7,367) — el 15.2% restante incluye referencias genéricas ("ley de la materia", "Reglamento de esta Ley") y leyes abrogadas
- La extracción de citas es por patrones de texto (regex), no NLP — puede perder referencias complejas
- El análisis es **estático** — no captura la evolución histórica de las reformas

---

## Correcciones Metodológicas Aplicadas

- **Artículos transitorios excluidos**: El parseador de artículos ahora detiene la extracción al encontrar la sección "TRANSITORIOS". Esto elimina citas de derogación/reforma que no representan dependencias funcionales entre leyes, reduciendo el total de citas de ~10,844 a 7,367 y los ciclos de 544 a 204.
- **Falsos positivos `direct_mention`**: Se añadió filtro de contexto para excluir citas en listas de derogación, preámbulos de decretos y referencias genéricas
- **Nodo fantasma CPEUM**: El ID hardcodeado `"constitucion-politica"` fue corregido a `"constitucion-politica-de-los-estados-unidos-mexicanos"` en el extractor de patrones constitucionales
- **LPEMEX falso alias**: El alias "Ley Orgánica de PEMEX" atraía todas las "Ley Orgánica de X" — eliminado
- **LFCE falso partial match**: El mecanismo de coincidencia parcial en lookup.py mapeaba todas las "Ley Federal de X" a LFCE — corregido priorizando el registro de corpus sobre coincidencias de baja confianza
- **Registro de corpus dinámico**: Resolución ampliada de 48 leyes hardcodeadas a las 318 del corpus completo

---

## Próximos Pasos Sugeridos

1. ~~Mejorar la clasificación de sectores~~ — resuelto: 0 leyes con sector desconocido (era 136); todas las comunidades etiquetadas
2. ~~Investigar las referencias huérfanas~~ — resuelto: 1,580 falsas alarmas corregidas; solo 18 referencias reales (todas a Ley de Vías Generales de Comunicación, abrogada)
3. ~~Análisis de simplificación regulatoria~~ — resuelto: 100 candidatas a abrogación (31%), 40 pares a fusionar, 40 a reformar
4. Verificar manualmente una muestra de las 195 dependencias circulares
5. Análisis temporal: incorporar fechas de reforma para ver cómo evoluciona la red

---

_Datos: diputados.gob.mx | Código: github.com/CoyStan/Genoma-Regulatorio-de-Mexico_
