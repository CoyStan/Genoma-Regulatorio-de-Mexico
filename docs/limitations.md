# Limitaciones — Genoma Regulatorio de México

## Cobertura del corpus

### ¿Qué se incluye?

- Leyes federales vigentes publicadas en el portal de la Cámara de Diputados.
- La Constitución Política de los Estados Unidos Mexicanos.
- Códigos federales (Civil, Penal, de Comercio, Fiscal, etc.).

### ¿Qué no se incluye (Phase 1)?

- **Reglamentos**: Los decretos reglamentarios no se mapean como nodos propios.
- **Normas Oficiales Mexicanas (NOMs)**: No están en el corpus principal.
- **Circulares y acuerdos administrativos**: Demasiado numerosos y cambiantes.
- **Leyes estatales**: El corpus es exclusivamente federal.
- **Tratados internacionales**: Se detectan referencias pero no se mapean como nodos.
- **Leyes abrogadas**: Se incluyen como nodos "stub" cuando son referenciadas, pero no se raspan sus textos.

---

## Limitaciones del raspado

### Dependencia de la estructura HTML

El raspador está diseñado para el formato HTML específico de `diputados.gob.mx`. Si el sitio cambia su estructura, el raspador puede fallar silenciosamente o producir texto corrupto. El checksum de cada archivo detecta cambios, pero no garantiza que el contenido extraído sea correcto.

### Codificación de caracteres

Algunos documentos históricos en el portal usan codificación Latin-1 en lugar de UTF-8. El raspador intenta detectar esto, pero puede haber caracteres mal interpretados en leyes antiguas.

### Leyes con múltiples versiones

Cuando una ley ha sido abrogada y sustituida por una nueva (ej. la antigua "Ley Federal de Radio y Televisión" vs. la "Ley Federal de Telecomunicaciones y Radiodifusión"), el portal puede mantener ambas versiones. El mapeo entre versiones históricas y actuales es manual.

---

## Limitaciones de la extracción de citas

### Cobertura estimada

Los patrones de regex capturan aproximadamente **70-80%** de las referencias cruzadas formulaicas. El 20-30% restante corresponde a:

- Referencias implícitas: "la ley de la materia", "la legislación aplicable"
- Referencias por número de DOF: "publicada en el D.O.F. el 15 de enero de 1970"
- Referencias nominales sin fórmula fija
- Tablas y anexos (difíciles de parsear)

### Falsos positivos

Pueden ocurrir cuando:
- Una ley cita otra ley por su nombre parcial, que coincide con el inicio del nombre de otra ley.
- El texto contiene títulos de leyes en contexto negativo ("no aplica lo dispuesto en...").

### Falsos negativos

No se detectan:
- Referencias con errores tipográficos en el nombre de la ley.
- Referencias en pies de página o notas (si el HTML no los incluye).
- Citas a artículos específicos sin mencionar el nombre de la ley fuente.

---

## Limitaciones de la resolución de entidades

### Ambigüedad

Algunos nombres parciales pueden mapearse a múltiples leyes. Por ejemplo:
- "Ley de Salud" puede referirse a la "Ley General de Salud" o a leyes estatales.
- "Ley Orgánica" es demasiado genérico sin más contexto.

El sistema conserva el mejor candidato con confianza reducida. Las resoluciones con score < 0.75 se marcan como "low" o "unresolved".

### Historicidad

Las leyes que han cambiado de nombre (como la LFTR, que sustituyó a la Ley Federal de Radio y Televisión) pueden no resolverse correctamente cuando se encuentra el nombre antiguo en leyes que no han sido actualizadas.

---

## Limitaciones de las métricas de red

### PageRank y la Constitución

La Constitución es el nodo con mayor in-degree y PageRank por amplio margen. Esto es esperado pero puede distorsionar las visualizaciones. Se puede excluir o escalar logarítmicamente para mejorar la legibilidad.

### Comunidades

El algoritmo de Louvain es no determinístico. Las comunidades detectadas varían ligeramente entre ejecuciones. Los resultados deben interpretarse como una aproximación, no como agrupaciones definitivas.

### Datos faltantes

Las leyes que no pudieron raspadas (por errores de red o formato no soportado) aparecen como nodos "stub" sin artículos ni citas de salida, lo que subestima su centralidad real.

---

## Limitaciones de los diagnósticos

### Lista de leyes abrogadas

La lista de leyes abrogadas en `07_diagnostics.py` es incompleta. Muchas leyes históricamente derogadas no están catalogadas, por lo que el número real de referencias huérfanas es mayor al reportado.

### Conflictos de definición

La detección de conflictos de definición es semántica y requiere revisión humana. Dos definiciones del mismo término pueden ser complementarias o específicas a contextos distintos, no necesariamente contradictorias.

---

## Contexto temporal

El corpus está anclado a la **fecha del raspado**. El sistema jurídico mexicano se reforma constantemente. En particular:

- Las **reformas constitucionales de 2024** (reforma judicial, eliminación de organismos autónomos como COFECE, IFT, INAI) modificaron sustancialmente el corpus. Leyes como la LFTR y la LFCE pueden estar en transición.
- Para análisis comparativos temporales, es necesario raspear en diferentes fechas y versionar los resultados.

---

## Limitaciones del aviso legal

**Este proyecto no es un servicio legal.**

Los resultados del análisis estructural tienen errores de extracción conocidos y deben ser verificados contra las fuentes primarias oficiales antes de cualquier uso en contexto legal, regulatorio o de asesoría.

La fuente oficial y definitiva de la legislación federal mexicana es el [Diario Oficial de la Federación](https://www.dof.gob.mx) y el portal de la [Cámara de Diputados](https://www.diputados.gob.mx/LeyesBiblio/).
