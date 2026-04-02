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
| Conexiones (citas entre leyes) | 4,497 |
| Densidad de la red | 0.045 |
| Comunidades regulatorias detectadas | 6 |
| Dependencias circulares (citas mutuas) | 500 |
| Leyes aisladas | 25 |
| Referencias huérfanas reales | 18 (todas a Ley de Vías Generales de Comunicación, abrogada) |

### Las 10 leyes más centrales (por PageRank)

Estas leyes son las más referenciadas — reformarlas tendría el mayor impacto en cascada sobre el resto del sistema:

1. **Constitución Política (CPEUM)** — citada por 316 de 318 leyes
2. **Ley General de Sociedades Mercantiles (LGSM)** — citada por 202 leyes
3. **Ley Orgánica del Poder Judicial de la Federación (LOPJF)** — citada por 137 leyes
4. **Ley Federal de Competencia Económica (LFCE)** — citada por 143 leyes
5. **Ley General de Educación (LGE)** — citada por 106 leyes
6. **Código Nacional de Procedimientos Penales (CNPP)** — citada por 101 leyes
7. **Ley Federal de Procedimiento Administrativo (LFPA)** — citada por 96 leyes
8. **Ley Orgánica de la Administración Pública Federal (LOAPF)** — citada por 90 leyes
9. **Ley Federal del Trabajo (LFT)** — citada por 92 leyes
10. **Ley en Materia de Telecomunicaciones y Radiodifusión (LFTR)** — citada por 82 leyes

### 6 Comunidades Regulatorias

| Comunidad | Leyes | Ley Central |
|-----------|-------|-------------|
| Constitucional | 98 | Constitución Política (CPEUM) |
| Financiero / Mercantil | 65 | Ley General de Sociedades Mercantiles |
| Administrativo / Regulación | 64 | Ley Federal de Competencia Económica |
| Fiscal / Cultural | 60 | Ley Federal del Derecho de Autor |
| Penal / Salud | 41 | Ley General de Salud |
| Administrativo / Procedimental | 33 | Ley Federal de Procedimiento Administrativo |

> _Nota: Con la corrección de nodos fragmentados el número de comunidades pasó de 7 a 6, al unificarse los stubs con sus nodos reales._

### 500 Dependencias Circulares

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

## Análisis de Simplificación Regulatoria

Basado en la red de citas, se cuantificó el potencial de reducir la complejidad del sistema legal federal.

| Métrica | Valor |
|---------|-------|
| Leyes candidatas a abrogación (score ≥ 80) | 160 (50% del corpus) |
| Leyes completamente aisladas (0 conexiones relevantes) | 23 |
| Pares candidatos a fusión (citan mutuamente, mismo sector) | 40 |
| Leyes que requieren reforma urgente (alta ambigüedad + ciclos) | 40 |

> _Nota: El número bajó de 217 a 160 tras corregir los nodos fragmentados — muchas leyes que parecían aisladas en realidad tienen dependencias reales._

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

1. ~~Mejorar la clasificación de sectores~~ — resuelto: 0 leyes con sector desconocido (era 136); todas las comunidades etiquetadas
2. ~~Investigar las referencias huérfanas~~ — resuelto: 1,580 falsas alarmas corregidas; solo 18 referencias reales (todas a Ley de Vías Generales de Comunicación, abrogada)
3. ~~Análisis de simplificación regulatoria~~ — resuelto: 160 candidatas a abrogación (50%), 40 pares a fusionar, 40 a reformar
4. Verificar manualmente una muestra de las 195 dependencias circulares
5. Análisis temporal: incorporar fechas de reforma para ver cómo evoluciona la red

---

_Datos: diputados.gob.mx | Código: github.com/CoyStan/Genoma-Regulatorio-de-Mexico_
