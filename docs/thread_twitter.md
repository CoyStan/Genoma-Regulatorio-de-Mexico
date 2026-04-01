# Hilo de Twitter — Genoma Regulatorio de México

> Imágenes: docs/assets/charts/

---

**[1/11] — GANCHO**

Analicé las 318 leyes federales de México como una red de citaciones.

10,844 conexiones. 7 comunidades. 195 ciclos. 50 términos jurídicos definidos diferente en distintas leyes.

El resultado: el 60% del corpus podría eliminarse sin romper el sistema.

🧵

---

**[2/11] — Qué construí**

Construí un "genoma regulatorio": cada ley es un nodo, cada vez que una ley menciona a otra es una arista.

318 leyes → 4,534 conexiones directas → red analizada con NetworkX y visualizada en 3D.

Código y datos: github.com/CoyStan/Genoma-Regulatorio-de-Mexico

---

**[3/11] — Las leyes más poderosas**
🖼️ chart_1_top10_leyes.png

Hay leyes que si se reforman, afectan en cascada a casi todo el sistema.

La CPEUM es citada por 316 de 318 leyes. Reformarla toca todo.

Pero hay otras menos obvias: la Ley General de Sociedades Mercantiles impacta a 269 leyes. La LFCE a 266.

---

**[4/11] — 7 comunidades regulatorias**
🖼️ chart_2_comunidades.png

El sistema no es plano. Agrupa naturalmente en 7 clústeres:

• Constitucional (98 leyes)
• Financiero/Mercantil (65)
• Administrativo/Regulación (64)
• Fiscal/Cultural (60)
• Penal/Salud (41)
• Procedimental (33)

---

**[5/11] — El problema de los ciclos**

195 pares de leyes se citan mutuamente. Eso es un ciclo:
A depende de B, B depende de A.

Ejemplos:
• Ley Federal del Trabajo ↔ Ley del Seguro Social
• Ley de Instituciones de Crédito ↔ Ley del Mercado de Valores

En ingeniería de software eso se llama deuda técnica. En derecho no tiene nombre.

---

**[6/11] — El 60% podría desaparecer**
🖼️ chart_3_abrogacion.png

217 de 318 leyes tienen un "score de seguridad" alto: pocas leyes dependen de ellas, impacto en cascada mínimo.

23 están completamente aisladas. Nadie las cita. No citan a nadie relevante.

¿Para qué existen?

---

**[7/11] — Leyes que podrían fusionarse**
🖼️ chart_5_fusion.png

40 pares de leyes se citan mutuamente, comparten sector y tienen baja dependencia externa.

Son candidatas a consolidarse en un solo instrumento jurídico más claro.

Menos leyes, menos confusión, misma cobertura.

---

**[8/11] — La misma palabra, definida diferente**
🖼️ chart_4_conflictos_definicion.png

50 términos están definidos de forma distinta en múltiples leyes.

"Secretaría" tiene 11 definiciones distintas.
"Ley" tiene 11.
"Comisión" tiene 10.

Esto no es ambigüedad accidental. Es complejidad acumulada por décadas sin coordinación.

---

**[9/11] — Las leyes que hay que reformar (no eliminar)**

Algunas leyes son demasiado importantes para abrogar pero concentran la mayor ambigüedad:

• Ley Federal de Fomento a Organizaciones de la Sociedad Civil
• Ley de la Comisión Nacional Bancaria y de Valores
• Ley del Seguro Social

Son nudos gordios del sistema: reformarlas bien aliviaría decenas de conflictos.

---

**[10/11] — La visualización**

Todo esto es navegable en 3D:

👉 coystan.github.io/Genoma-Regulatorio-de-Mexico

Puedes buscar cualquier ley, ver qué artículos cita y cuáles la citan, y explorar la red por sector.

---

**[11/11] — Por qué importa**

México tiene uno de los sistemas legales federales más fragmentados de América Latina.

Más leyes ≠ más justicia. Más leyes = más ambigüedad, más costo de cumplimiento, más espacio para la discrecionalidad.

Este proyecto intenta medir eso con datos.

¿Qué ley abrogarias tú primero?

---

_Herramientas: Python · NetworkX · matplotlib · Three.js · GitHub Pages_
_Datos: diputados.gob.mx_
