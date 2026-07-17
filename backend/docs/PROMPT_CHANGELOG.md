# Historial de versiones del Prompt

Reconstruido a partir del codigo y las tareas realmente ejecutadas (no a partir de commits
granulares por cambio: el repo tiene un unico commit inicial y un commit posterior que agrupa
varias tareas, sin separacion por cambio de prompt). Regla vigente de aca en adelante: **todo
cambio futuro al `SYSTEM_PROMPT` en `services/llm_connector.py` debe venir acompanado de un bump
de `PROMPT_VERSION` + una entrada nueva aca.**

## v1.0 — Diseno inicial (rol, contexto, guardrails y Response Schema)

Version con la que se implemento el pipeline completo desde el scaffold inicial del proyecto:
rol de "Ingeniero de Software Senior" con enfoque educativo, instruccion de responder unicamente
con el Response Schema en JSON (sin markdown), y **los guardrails de la seccion 8 del PDF de
arquitectura** (no afirmar ejecucion, diferenciar errores/mejoras/recomendaciones, tono educativo,
no inventar informacion, etc.). A diferencia de lo que podria asumirse, los guardrails no se
agregaron en una iteracion posterior: la tarea de scaffold original ya pedia implementar el
pipeline "tal como lo documenta el PDF", que incluye esa seccion desde el principio - por eso
quedan agrupados en esta misma version inicial y no como un v1.1 separado.

## v1.1 — Contexto de regeneracion

Se agrego `_build_regeneration_context()` y los parametros opcionales `previous_review` /
`motivo_regeneracion` a `_build_prompt()`/`analizar_codigo()`, para el endpoint
`POST /api/reviews/<id>/regenerate` (seccion 5.4 del PDF: variables opcionales del prompt).
Cuando aplica, el prompt incluye un bloque adicional con la evaluacion anterior y el motivo por
el que el estudiante pidio una nueva revision.

## v1.2 — Few-Shot Examples condicionales

Se agrego `FEW_SHOT_EXAMPLES` (seccion 5.5 del PDF) y un segundo intento condicional en
`analizar_codigo()`: el primer intento de cualquier analisis sigue sin incluir ejemplos (para no
inflar el prompt en el caso normal, que ya funcionaba bien); si el Response Validator rechaza esa
primera respuesta, se hace un unico reintento adicional con 1 ejemplo completo de entrada/salida
incluido en el prompt, para reforzar el formato esperado - exactamente el uso condicional que
describe el PDF ("se utilizaran unicamente cuando sea necesario reforzar el formato esperado"),
no un ejemplo enviado siempre. Este reintento es independiente del loop de reintentos por fallas
transitorias de red/parseo (`MAX_ATTEMPTS` en `_call_llm`) - no comparten contador.
