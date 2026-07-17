# Auditoría del Backend — Sistema Inteligente de Revisión de Código para Estudiantes

**Fecha:** 2026-07-17
**Alcance:** Solo backend (`backend/`). No se modificó ningún archivo de código para esta auditoría.
**Metodología:** Relectura completa de los dos PDF originales (recuperados de su ubicación real en
`Desktop/ESEN/4TO AÑO/CICLO II/Programación con IA/PROYECTO FINAL/Parte Erick/`, ya que la copia
de trabajo en la raíz del repo había sido eliminada), relectura de todo el código actual, y
**verificación empírica en vivo** de cada afirmación no trivial (no se asumió nada por lo que dijera
un resumen de una tarea anterior). Cada hallazgo marcado como confirmado fue efectivamente
reproducido con el servidor corriendo o con un script aislado.

---

## Resumen ejecutivo

El módulo de IA (pipeline completo, guardrails, Response Schema) está sólidamente implementado y
**verificado en vivo** en esta auditoría, incluyendo el camino de rechazo del Response Validator que
nunca se había probado explícitamente. La persistencia, autenticación JWT (JWKS/ES256) y CORS
funcionan correctamente y de forma consistente entre sí. Sin embargo, esta auditoría encontró **dos
gaps de seguridad/robustez no detectados antes**: `GET /api/reviews/<id>` no aplica ningún ownership
check (expone datos privados de estudiantes autenticados a cualquiera con el UUID, confirmado
creando un usuario real y leyendo su revisión sin token), y el handler JSON de error 500 es código
muerto mientras `DEBUG=True` (la configuración real actual) — un crash no anticipado devuelve HTML,
no el JSON documentado. El proyecto no tiene testing automatizado tipo pytest, no tiene preparación
de despliegue (Docker/Procfile/WSGI de producción), y no tiene rate limiting ni límites de tamaño de
input, lo cual son riesgos reales de cara a una demo o entrega con tráfico real.

---

## 1. Fidelidad al documento de arquitectura original

### Componentes del pipeline (sección 5 del PDF)

| Componente | Estado | Detalle |
|---|---|---|
| 5.1 Input Processor | ✅ Implementado | `_process_input()` en `services/llm_connector.py`. Valida los 5 campos requeridos, limpia (`.strip()`) y normaliza. Coincide exactamente con lo descrito. |
| 5.2 Prompt Builder | ✅ Implementado | `_build_prompt()`. Combina System Prompt + Variables + Response Schema + contexto de regeneración. Es el componente central, tal como pide el PDF. |
| 5.3 System Prompt | ✅ Implementado | Constante `SYSTEM_PROMPT` en el módulo. Ver guardrails abajo — cité el texto real, no asumí que estaba. |
| 5.4 Variables del Prompt | ⚠️ Parcial | Las 5 obligatorias (`language`, `exercise`, `level`, `review_type`, `student_code`) están completas. De las 3 opcionales que lista el PDF (`observaciones`, `revisión anterior`, `motivo de regeneración`): **`revisión anterior` y `motivo de regeneración` sí se implementaron** (parámetros `previous_review`/`motivo_regeneracion` de `analizar_codigo`, usados por `/regenerate`). **`observaciones` nunca se implementó** — no aparece en ningún lado del código, tampoco como parte de la regeneración. |
| 5.5 Few-Shot Examples | ❌ Falta | Confirmado: no hay ningún ejemplo de entrada/salida embebido en el prompt en ningún punto del código. El PDF dice que se usan "cuando sea necesario reforzar el formato esperado" — esto nunca se incorporó, ni siquiera de forma rudimentaria. Es un gap real, no una omisión de este reporte. |
| 5.6 LLM Service | ✅ Implementado | `_call_llm()` + `_get_client()`. Autenticación perezosa, configuración, envío, recepción, manejo de errores y reintentos — los 6 puntos que pide el PDF, todos presentes. |
| 5.7 Output Parser | ✅ Implementado | `_clean_output_text()`. Extrae el JSON entre `{` y `}`, elimina backticks/markdown. |
| 5.8 Response Validator | ✅ Implementado y **verificado en vivo** | `_validate_response()` con `jsonschema`. Probé 3 casos deliberadamente rotos (campo requerido faltante, valor de enum inválido, `score` fuera de rango) y los 3 fueron rechazados correctamente, con log `❌` claro y excepción controlada (`ResponseValidationError`), sin romper la app. Antes de esta auditoría esto solo se había probado con respuestas que sí cumplían. |

### Few-Shot Examples (5.5) — explícito

**❌ Falta.** No se implementó nunca. Ninguna tarea anterior lo abordó.

### Prompt Versioning (7.5)

**❌ Falta, confirmado.** No existe ningún mecanismo — ni un comentario de versión, ni un changelog,
ni una constante `PROMPT_VERSION`. El `SYSTEM_PROMPT` se ha modificado varias veces a lo largo de las
tareas (se agregaron los guardrails, después el bloque de regeneración) sin ningún registro de qué
cambió entre versiones. El PDF pide explícitamente una tabla tipo v1.0/v1.1/v1.2.

### Guardrails (sección 8) — texto real citado

Leí `services/llm_connector.py:49-62` (no asumí). El `SYSTEM_PROMPT` actual dice, literalmente:

```
- No afirmes que el codigo funciona ni que ha sido ejecutado.
- No asumas resultados de ejecucion: el codigo no se ejecuta en este proceso.
- Diferencia claramente entre errores, mejoras y recomendaciones.
- Explica cada hallazgo (por que ocurre, que impacto tiene y como corregirlo).
- Manten un lenguaje educativo, claro y respetuoso, pensado para un estudiante.
- No inventes informacion que no puedas sustentar con el codigo recibido.
- Evita cualquier contenido fuera del contexto de revision de codigo.
- Responde UNICAMENTE con un objeto JSON que cumpla de forma exacta el Response Schema...
```

Los 8 guardrails de la sección 8 del PDF están **✅ todos presentes**, casi palabra por palabra.

### Configuración del modelo (sección 9)

| Parámetro | PDF | Código actual | Estado |
|---|---|---|---|
| Modelo | GPT-4.1 / GPT-4o / Gemini 2.5 Pro | `gemini-flash-lite-latest` | ⚠️ Parcial — decisión justificada en una tarea anterior (`gemini-2.0-flash-lite` tenía cupo gratuito en 0 para el proyecto de Supabase/Google usado), pero es un modelo de tier "lite", no "Pro" como sugería el documento. Vale la pena que el equipo lo sepa explícitamente: puede afectar la profundidad del análisis. |
| Temperature | 0.2 | `0.2` | ✅ |
| Top P | 1.0 | `1.0` | ✅ |
| Max Tokens | 2000 | `max_output_tokens: 2000` | ✅ |
| Frequency Penalty | 0 | No configurado | ⚠️ Verifiqué que el SDK de `google-genai` sí soporta `frequency_penalty`/`presence_penalty` en `GenerateContentConfig`, pero el código no los setea. No configurado probablemente se comporta igual que 0 en la práctica, pero no está explícito ni verificado. |
| Presence Penalty | 0 | No configurado | ⚠️ Igual que arriba. |

---

## 2. Cumplimiento del Response Schema

- **¿La respuesta real cumple el schema en el 100% de los casos, incluyendo límite?** ✅ Sí, y no por
  suposición: cada `POST /api/review` o `/regenerate` que devuelve `200` **necesariamente** pasó
  `_validate_response()` en el servidor (si no pasara, el endpoint devuelve `503`, nunca `200`). Los
  casos ya probados con `200` incluyen código con error de sintaxis real (caso 4). El caso "código
  vacío" nunca llega al LLM — se corta antes en el Input Processor (`400`), así que no aplica el
  Response Schema ahí; es consistente con el diseño, no un gap.
- **¿El Response Validator rechaza correctamente respuestas que no cumplen?** ✅ Confirmado en vivo
  en esta auditoría (ver sección 1, Response Validator) con 3 casos rotos distintos. Antes de esta
  auditoría, esto **nunca se había probado explícitamente** — solo se había visto funcionar con
  respuestas válidas.

---

## 3. Seguridad

| Punto | Estado | Detalle |
|---|---|---|
| ¿Credenciales hardcodeadas en el repo? | ✅ Ninguna | Grep exhaustivo (patrones de API keys de Google, JWT-like strings, asignaciones directas) sobre todo `.py`/`.md`/`.json`/`.sql`/`.txt` del proyecto: cero coincidencias reales (solo los `os.getenv(...)` esperados). |
| ¿`.env` versionado por error? | ✅ No | Existe un repo git real en la raíz del proyecto (no lo inicié yo). `git ls-files` confirma que `.env` **no** está trackeado; `git status --short` está limpio. |
| Ownership check de `/regenerate` y `/history` | ✅ Robusto | Repasé `services/review_ownership.py` línea por línea: un `session_id` coincidente nunca desbloquea una revisión con `student_id` no nulo (se ignora por completo en ese branch), y viceversa un JWT válido no sirve para una revisión anónima si no se manda también el `session_id` exacto. Los 4 casos de test (13-16) lo ejercitan con datos reales (usuario autenticado real vía Auth Admin API, no simulado). |
| **`GET /api/reviews/<id>` — ownership check** | ❌ **Falta (hallazgo nuevo de esta auditoría)** | Este endpoint **no llama a `review_ownership.is_owner()` en ningún punto** — simplemente busca por id y devuelve la fila completa a quien sea. Lo confirmé creando un usuario real, generando una revisión suya con un `student_code` marcado, y leyéndola con `GET /api/reviews/<id>` **sin ningún token**: devolvió `200` con el `student_code` y el `student_id` del dueño completos. Es inconsistente con el modelo de ownership que sí se aplicó a `/regenerate` y `/history` para el mismo recurso — probablemente un descuido de cuando se agregó ownership (esa tarea solo tocó los dos endpoints nuevos, no revisó el `GET` que ya existía de antes). El `review_id` es un UUID v4 (no enumerable a fuerza bruta), así que no es un "listado abierto", pero cualquiera que obtenga/filtre/loguee ese id en cualquier lugar (URL compartida, log de un proxy, etc.) puede leer el código y la identidad del estudiante sin autenticarse. |
| Token expirado real | ⚠️ No probado | El caso 10 usa un JWT inventado (mal formado), y los casos 12/16 usan JWT reales recién emitidos por Supabase (expiran en ~1h, nunca se esperó ni se forzó su vencimiento). `PyJWT` valida `exp` por defecto, así que la lógica debería funcionar, pero **nunca se verificó con un token genuinamente vencido**. |
| CORS + JWT juntos | ✅ Verificado (tarea anterior, re-confirmado en esta auditoría por lectura de código) | Origen permitido agrega `Access-Control-Allow-Origin`; origen no listado no lo agrega; preflight `OPTIONS` con `Authorization` funciona. |
| ¿Algún endpoint que debería requerir auth y no la requiere (o viceversa)? | Ver el hallazgo de `GET /api/reviews/<id>` arriba — es el ejemplo concreto. El resto de los endpoints tienen el nivel de auth que documentan (verificado contra `/api/openapi.json`). |

---

## 4. Manejo de errores y robustez

| Punto | Estado | Detalle |
|---|---|---|
| ¿Todos los endpoints devuelven JSON consistente? | ⚠️ **No siempre — hallazgo nuevo** | Probé en vivo: con `DEBUG=True` (que es la configuración real actual, vía `FLASK_ENV=development` en `.env`), una excepción **no capturada** en una vista devuelve `Content-Type: text/html` (el debugger interactivo de Werkzeug), **no** el JSON `{"error": "Error interno del servidor."}` que define el `@app.errorhandler(500)`. Ese handler personalizado solo se activa cuando `DEBUG=False`. En el estado actual del `.env`, cualquier bug no anticipado que llegue a producir una excepción sin capturar rompería el contrato de "siempre JSON". No encontré ningún camino real hoy que dispare esto (todo el manejo de errores de negocio ya está bien capturado), pero el mecanismo de defensa de último recurso no funciona en la config actual. |
| ¿Los reintentos ante fallos transitorios realmente reintentan? | ✅ Verificado en vivo (más allá del 429) | Simulé un error genérico (HTTP 500) del LLM 3 veces seguidas: el código reintentó exactamente `MAX_ATTEMPTS=3` veces antes de fallar con `LLMCommunicationError` controlado. El único mockeado en `test_api_manual.py` es el camino 429 (sin reintento, por diseño correcto) — el camino de reintento genérico nunca estuvo cubierto por el script automatizado, solo lo verifiqué manualmente en esta auditoría. |
| `student_code` extremadamente largo | ❌ Sin límite en ningún nivel | No hay `MAX_CONTENT_LENGTH` configurado en Flask (acepta cualquier tamaño de body en memoria), el Input Processor no valida longitud, y la columna `student_code` en Postgres es `text` sin límite. Un input enorme se intentaría mandar igual a Gemini; si el proveedor lo rechaza (límite de tokens), ese error entraría al mismo loop de reintentos genérico (3 intentos inútiles, ya que no es un fallo transitorio) antes de fallar con `502` — no rompe la app, pero es ineficiente y no hay ningún control temprano. |
| Respuesta del LLM completamente inesperada (no-JSON, prosa libre) | ⚠️ Implementado, no probado | El Output Parser lanza `LLMCommunicationError` si no encuentra `{`/`}`, lo cual entra al mismo loop de reintentos y termina en `502` — diseño correcto por lectura de código, pero no hay ningún test (mock o real) que fuerce este escenario específico. |

---

## 5. Testing

| Punto | Estado | Detalle |
|---|---|---|
| Cobertura de los 16 casos de `test_api_manual.py` | ⚠️ Buena pero con huecos reales | Cubre bien el camino feliz, validación de input, esquema, cuota (mock), JWT inválido/ausente, y ownership básico de regeneración. **No cubre**: `GET /api/reviews/<id>/history` con una cadena de más de 2 niveles (regenerar una regeneración) — el código de `list_review_history` fue escrito para soportar profundidad arbitraria pero nunca se probó con 3+ niveles; el caso donde la persistencia en Supabase falla pero el LLM sí respondió (se probó manualmente en una tarea anterior contra una tabla inexistente, pero no hay un caso automatizado hoy); el gap de `GET /api/reviews/<id>` sin ownership (obviamente, nadie lo buscó hasta ahora); reintentos no-429; y tokens realmente expirados. |
| ¿Existen tests automatizados tipo pytest? | ❌ No | Confirmé que `pytest` **ni siquiera está instalado** en el venv (`pip show pytest` → not found) ni está en `requirements.txt`. Todo el testing depende de `tests/test_api_manual.py` (un script standalone con inspección visual del resumen ✅/❌) y de `tests/test_mock_connection.py`/`test_llm_connection.py` (scripts sueltos, ejecutables a mano, no una suite). No hay forma de correr esto en un pipeline de CI tal cual está. |

---

## 6. Documentación y developer experience

| Punto | Estado | Detalle |
|---|---|---|
| ¿Alguien nuevo podría levantar el proyecto solo con el README? | ✅ Mayormente sí | Instalación, variables de entorno, migraciones (en orden), cómo correr el servidor y los tests, estructura de carpetas — todo está. Asume que la persona ya tiene acceso al proyecto de Supabase del equipo (razonable, no es un gap). |
| Detalle menor de código desactualizado | ⚠️ | `tests/test_llm_connection.py` imprime `"--- Probando conexion con Gemini (gemini-2.0-flash-lite) ---"`, pero el modelo real configurado hace varias tareas es `gemini-flash-lite-latest`. Es solo un string de log, no afecta funcionalidad, pero puede confundir a alguien debuggeando. |
| ¿La spec de OpenAPI está sincronizada? | ✅ Verificado en vivo | Comparé `GET /api/openapi.json` contra `app.url_map.iter_rules()` directamente (dos fuentes independientes): los 7 endpoints documentados coinciden exactamente con las rutas registradas, incluyendo `/regenerate` y `/history` de la tarea más reciente. No hay drift. |

---

## 7. Preparación para producción / demo final

| Punto | Estado | Detalle |
|---|---|---|
| Configuración de despliegue (Docker/Procfile/Render/Railway) | ❌ No existe | Confirmé con búsqueda directa en la raíz del backend: no hay `Dockerfile`, `Procfile`, ni ningún YAML de despliegue. Hoy el proyecto solo corre en local. |
| Servidor WSGI de producción | ❌ No existe | `requirements.txt` no incluye `gunicorn`/`waitress`/`uwsgi`. Solo el servidor de desarrollo de Flask/Werkzeug (que imprime su propia advertencia de "no usar en producción" en cada arranque). |
| Rate limiting | ❌ No existe | No hay `flask-limiter` ni ningún throttling manual por IP/sesión. Nada impide que alguien agote la cuota de Gemini con un loop de requests a `/api/review` (ya vimos en una tarea anterior que la cuota gratuita es limitada y se agota fácil). |
| ¿El logging actual alcanza para producción? | ⚠️ Suficiente para dev, no para producción | Va a stdout con formato legible para humanos (`timestamp [LEVEL] logger: mensaje`) — lo usamos activamente para debuggear en tareas anteriores y funciona bien para eso. Pero no es JSON estructurado, no tiene nivel configurable por variable de entorno, no rota archivos, y no hay integración con ningún agregador (Sentry, CloudWatch, etc.). Si el proyecto se despliega, hoy no habría forma de ver estos logs fuera de la terminal del servidor. |

---

## 8. Gaps fuera del documento de arquitectura original (pero necesarios para un producto real)

- **Paginación**: ❌ ninguno de los endpoints de listado (`/api/reviews?session_id=`, `/api/reviews/mine`, `/api/reviews/<id>/history`) tiene límite ni paginación. Un estudiante con cientos de revisiones recibiría todas en una sola respuesta.
- **Límites de longitud**: ❌ ni `exercise` ni `motivo_regeneracion` ni `student_code` tienen límite de caracteres, ni a nivel de aplicación ni en la base de datos (columnas `text` sin restricción en Postgres).
- **`MAX_CONTENT_LENGTH`**: ❌ no configurado en Flask (relacionado con el punto de robustez de la sección 4).
- **Frontend**: ahora existe una carpeta `frontend/` (Vite + React + TypeScript) en la raíz del proyecto — fuera del alcance de esta auditoría, pero vale mencionar que CORS y la documentación ya están listos para que se conecte cuando corresponda.
- **Structured Output nativo de Gemini**: confirmé que `GenerateContentConfig` del SDK soporta `response_mime_type`/`response_schema` (JSON mode nativo del proveedor). No es un gap — el Output Parser manual actual funciona y está bien probado — pero es una oportunidad real de robustecer el parseo delegándolo al proveedor en vez de al parsing manual de texto.

---

## Recomendaciones priorizadas

### Crítico
1. **Agregar ownership check a `GET /api/reviews/<id>`** (mismo criterio que `/regenerate`/`/history`) — hoy expone datos privados de estudiantes autenticados a cualquiera con el UUID. Confirmado con un exploit real en esta auditoría.
2. **Resolver que el handler JSON de 500 no funciona con `DEBUG=True`** — o se corrige la configuración para producción/demo, o se agrega un mecanismo que garantice JSON incluso en modo debug. Hoy un crash no anticipado rompe el contrato "todo devuelve JSON".
3. **Límite de tamaño de input** (`MAX_CONTENT_LENGTH` en Flask + validación de longitud de `student_code` en el Input Processor) — sin esto, cualquiera puede mandar payloads enormes y gastar cuota de Gemini sin control.
4. **Rate limiting** en `/api/review` y `/regenerate` como mínimo — sin esto, un loop simple agota la cuota gratuita de Gemini para todo el equipo.

### Importante
5. Implementar **Prompt Versioning** (sección 7.5 del PDF) — aunque sea un comentario con historial de versiones del `SYSTEM_PROMPT`.
6. Decidir qué hacer con **Few-Shot Examples** (sección 5.5) — está documentado como gap explícito desde el PDF original y nunca se abordó.
7. Sumar una **suite de tests automatizados tipo pytest** (con asserts reales, sin necesidad de correr el servidor a mano) — al menos para el Response Validator, el Input Processor y el ownership check, que son lógica pura fácil de testear sin red.
8. Cubrir los casos de test que faltan: cadena de historial de 3+ niveles, fallo de persistencia con LLM exitoso, reintentos no-429, token realmente expirado.
9. Definir **preparación de despliegue** (Dockerfile o equivalente, servidor WSGI de producción) antes de una demo real fuera de `localhost`.

### Nice to have
10. Implementar la variable opcional `observaciones` (sección 5.4) si el equipo la considera útil.
11. Configurar explícitamente `frequency_penalty`/`presence_penalty` (o documentar por qué se dejan sin configurar).
12. Evaluar si vale la pena subir de tier de modelo (de `gemini-flash-lite-latest` a algo más parecido a "Gemini 2.5 Pro") para mejorar la profundidad del análisis, si el presupuesto/cuota lo permite.
13. Agregar paginación a los endpoints de listado.
14. Agregar límites de longitud a `exercise`/`motivo_regeneracion`.
15. Estructurar el logging para producción (JSON, nivel configurable, integración con un agregador).
16. Corregir el string de log desactualizado en `tests/test_llm_connection.py`.
17. Evaluar migrar a Structured Output nativo de Gemini como complemento del Output Parser manual.

---

## Addendum — Resolución de los hallazgos Críticos (2026-07-17)

Los 4 puntos de la sección "Crítico" de este mismo documento fueron corregidos. Alcance estricto:
solo esos 4 — nada de "Importante" ni "Nice to have" se tocó en esta tarea. Los 16 casos originales
de `tests/test_api_manual.py` siguen pasando (dos de ellos, detallados abajo, necesitaron un ajuste
menor porque el propio fix de seguridad cambia el contrato que ejercitaban), y se agregaron los
casos 17-21. Verificado en vivo: **21/21 casos OK**.

1. **Ownership check en `GET /api/reviews/<id>`** ✅ Resuelto. El endpoint ahora llama a
   `services/review_ownership.py:is_owner()` — el mismo criterio, sin reimplementarlo — antes de
   devolver la fila: revisión de un estudiante autenticado exige JWT propio; revisión anónima exige
   `session_id` exacto como query param. `review_id` inexistente sigue devolviendo `404` antes que
   la verificación de ownership. Caso 17 reproduce el exploit exacto de la auditoría (usuario real
   vía Auth Admin API, lectura sin token ni session_id) y confirma `403`, y confirma también que el
   dueño real sigue pudiendo leerla (`200`).
   **Efecto secundario esperado:** el caso 8 preexistente (lectura de una revisión anónima) pasó a
   mandar el `session_id` del caso feliz, porque ahora es obligatorio para leer una revisión anónima
   — antes de este fix, no mandarlo funcionaba porque el endpoint era completamente público (el bug
   que esta auditoría encontró). Es el único cambio de comportamiento esperado en un caso existente,
   consecuencia directa y necesaria del fix; el caso sigue verificando lo mismo (lectura exitosa por
   id) bajo el contrato correcto.

2. **JSON garantizado en errores no controlados, incluso con `DEBUG=True`** ✅ Resuelto — sin tocar
   `DEBUG` ni `PROPAGATE_EXCEPTIONS`. Se agregó `@app.errorhandler(Exception)` en `app.py`. Causa
   raíz real (más específica que lo que decía el hallazgo original): `@app.errorhandler(500)` **nunca
   atrapa una excepción de Python genérica** (solo `abort(500)`/`InternalServerError` explícitos) —
   es un comportamiento estándar de Flask, no específico de este proyecto, y por eso cambiar `DEBUG`
   a `False` tampoco lo hubiera arreglado. Registrar el handler para la clase base `Exception` sí
   la intercepta, porque Flask la resuelve en `handle_user_exception` antes de mirar
   `PROPAGATE_EXCEPTIONS`/modo debug.
   **Trade-off real, explícito (tal como pidió la tarea, no se decidió en silencio):** con este
   handler activo, el debugger interactivo HTML de Werkzeug **ya no aparece nunca**, ni siquiera con
   `DEBUG=True`, porque Flask maneja la excepción internamente antes de que el WSGI de Werkzeug la
   vea. El traceback completo se sigue viendo igual en la terminal (via `logger.exception(...)` en el
   handler), asi que no se pierde la información para debuggear a mano — se pierde únicamente la
   posibilidad de ejecutar código en el stack frame desde el navegador (`evalex`). Se consideró
   razonable priorizar el contrato JSON consistente para el frontend por sobre esa conveniencia
   puntual; si en algún momento se quiere recuperar el debugger interactivo para una sesión de debug
   específica, alcanza con comentar temporalmente ese `@app.errorhandler(Exception)`.
   Caso 18 fuerza un crash real vía `GET /api/_internal/test-crash` (ruta que solo existe cuando
   `DEBUG=True`, pensada exclusivamente para este test) y confirma `500` en JSON.

3. **Límite de tamaño de input** ✅ Resuelto en dos niveles. `MAX_CONTENT_LENGTH` de Flask
   (`MAX_REQUEST_SIZE_BYTES`, default 100 KB) rechaza con `413` JSON cualquier body mayor (caso 19).
   El Input Processor (`services/llm_connector.py:_process_input`) valida por separado la longitud de
   `student_code` (`MAX_STUDENT_CODE_CHARS`, default 20000 caracteres — generoso para un ejercicio de
   estudiante típico, muy por debajo del límite de bytes del request) y corta con `400` antes de
   construir el prompt o llamar al LLM (caso 20, con un body chico que no toca el límite de 413,
   para probar específicamente este segundo nivel).

4. **Rate limiting** ✅ Resuelto con `flask-limiter`. `POST /api/review` y
   `POST /api/reviews/<id>/regenerate` tienen un límite por IP (`REVIEW_RATE_LIMIT`, default **30 per
   minute** — se subió del "10 per minute" sugerido como ejemplo en la tarea original porque, contando
   las llamadas reales que ya hace la propia suite de 21 casos en una corrida, un límite de 10
   quedaría al borde de auto-dispararse con uso legítimo, y 30 sigue siendo muy por debajo de lo que
   generaría un loop abusivo). Al superarse, responde `429` en JSON con un mensaje que aclara
   explícitamente que es un límite propio del backend, distinto de la cuota de Gemini. Nota real: hoy
   esa distinción no genera ambigüedad en la práctica, porque cuando Gemini devuelve 429 (cuota
   agotada), el backend ya lo traduce a `502` (`QuotaExceededError` en `routes/review.py`), nunca a
   `429` — así que un `429` que ve el cliente siempre es del backend. El mensaje explícito se dejó
   igual, pensando en si en el futuro cambia esa traducción. Caso 21 (el último del script, a
   propósito: agota el límite para el resto de la ventana de 1 minuto) dispara una ráfaga de
   requests que devuelven `400` rápido (sin gastar cuota real de Gemini, porque el rate limiter
   cuenta el hit antes de que la vista se ejecute) hasta confirmar el `429`.

**Variables de entorno nuevas** (documentadas en `.env.example` y `README.md`): `MAX_REQUEST_SIZE_BYTES`,
`MAX_STUDENT_CODE_CHARS`, `REVIEW_RATE_LIMIT`. Todas tienen default razonable — no son obligatorias
para levantar el proyecto. La spec de OpenAPI (`/api/openapi.json`) ya refleja `403`/`413`/`429` en
los endpoints donde corresponde (verificado en vivo comparando contra `app.url_map`, igual que en la
auditoría original).

Lo que sigue sin tocar, a propósito, por estar fuera del alcance de esta tarea: Prompt Versioning,
Few-Shot Examples, suite de pytest, cobertura de tests faltante (historial 3+ niveles, reintentos
no-429, token expirado real), preparación de despliegue, y todo lo demás de "Importante"/"Nice to
have".

---

## Addendum 2 — Few-Shot Examples + Prompt Versioning (2026-07-17)

Resueltos los puntos 5 y 6 de la sección "Importante". Alcance estricto: solo estos dos (agrupados
porque tocan el mismo componente, `SYSTEM_PROMPT`/Prompt Builder) — nada más de "Importante"/"Nice
to have" se tocó. Los 21 casos previos siguen pasando sin cambios; se agregaron los casos 22 y 23.
Verificado en vivo: **23/23 casos OK**.

5. **Few-Shot Examples (sección 5.5 del PDF)** ✅ Resuelto — se decidió implementarlo (no solo
   documentar la omisión). Diseño condicional, tal como pide el PDF ("se utilizarán únicamente
   cuando sea necesario reforzar el formato esperado"): el primer intento de cualquier análisis
   sigue sin incluir ejemplos, para no inflar el prompt en el caso normal (caso 22 confirma que el
   primer intento NO contiene el bloque de ejemplos). Si el Response Validator rechaza esa primera
   respuesta, `analizar_codigo()` hace **un único reintento adicional** con `FEW_SHOT_EXAMPLES`
   (un ejemplo completo de entrada/salida) agregado al prompt — separado y con contador propio,
   sin mezclarse con `MAX_ATTEMPTS` (los reintentos por fallas transitorias de red/parseo dentro de
   `_call_llm`). El log distintivo (`⚠️ Response no valido en el primer intento, reintentando con
   Few-Shot Examples`) se verificó en vivo capturando el logger, no solo por inspección visual
   (caso 22). Si ese segundo intento también falla la validación, se sigue propagando
   `ResponseValidationError` exactamente igual que antes (caso 23) — el mecanismo de refuerzo no
   cambia el comportamiento de fallo real.
   **Corrección sobre el enunciado de esta tarea:** el caso 23 pide confirmar que la falla devuelve
   `502` — el código real (`routes/review.py`, sin cambios en esta tarea) mapea
   `ResponseValidationError` a **`503`**, no `502` (`502` es solo para `LLMCommunicationError`,
   fallos de comunicación con el proveedor). Los tests verifican la excepción real
   (`ResponseValidationError`), que es lo que efectivamente produce el `503` documentado en Swagger
   desde la tarea de CORS/OpenAPI — no se cambió ningún código de status para esta tarea.

6. **Prompt Versioning (sección 7.5 del PDF)** ✅ Resuelto. Se agregó `PROMPT_VERSION` en
   `services/llm_connector.py`, logueada en `INFO` en cada llamada real a Gemini (junto con el
   modelo y el número de intento) — no como parte de la respuesta al usuario. Se creó
   `docs/PROMPT_CHANGELOG.md` con el historial reconstruido a partir del código real, no del
   ejemplo de estructura que traía el enunciado de la tarea: los guardrails de la sección 8 no
   fueron un incremento separado (`v1.1` en el ejemplo sugerido) — ya estaban en el `SYSTEM_PROMPT`
   desde el scaffold inicial del proyecto, porque esa tarea ya pedía implementar el pipeline "tal
   como lo documenta el PDF". Por eso el historial real quedó en 3 versiones, no 4
   (`v1.0` diseño inicial + guardrails, `v1.1` contexto de regeneración, `v1.2` few-shot
   condicionales) y `PROMPT_VERSION` quedó en `"1.2"`, no en `"1.3"` como sugería el ejemplo del
   enunciado. Se dejó un comentario explícito arriba de `PROMPT_VERSION`/`SYSTEM_PROMPT` en el
   código recordando que cualquier cambio futuro al prompt debe venir con bump de versión + entrada
   nueva en el changelog.

**Archivos nuevos de esta tarea:** `docs/PROMPT_CHANGELOG.md`. **Archivos modificados:**
`services/llm_connector.py` (Few-Shot Examples, `PROMPT_VERSION`, logging), `tests/test_api_manual.py`
(casos 22-23), este documento.

---

## Addendum 3 — Suite de pytest + cobertura de casos faltantes (2026-07-17)

Resueltos los puntos 7 y 8 de la sección "Importante". Alcance estricto: solo estos dos — no se
tocó el punto 9 (Docker/despliegue), ni nada de "Nice to have". `tests/test_api_manual.py` **no se
eliminó ni se reemplazó**: sigue existiendo como test de integración end-to-end, y sus 24 casos
(los 23 previos + el nuevo de historial de 3+ niveles) se verificaron pasando contra el servidor y
el Supabase reales. Se sumó una capa nueva, no se quitó nada.

7. **Suite de `pytest` para lógica sin red** ✅ Resuelto. `tests/unit/` (config mínima en
   `pytest.ini`: `testpaths = tests/unit` + `pythonpath = .`, para que `pytest` corrido desde
   `backend/` encuentre los tests e importe `services.*`/`repositories.*`/`app` sin configuración
   extra) con 7 archivos:
   - `test_input_processor.py` — campos requeridos, campo faltante, `student_code` vacío (mismo
     criterio ya decidido: se trata como campo faltante), `student_code` que excede
     `MAX_STUDENT_CODE_CHARS`.
   - `test_response_validator.py` — respuesta válida, campo requerido faltante, `enum` inválido
     (`severity`), `score` fuera de rango.
   - `test_review_ownership.py` — las 4 combinaciones pedidas (autenticado propio/ajeno, anónimo
     coincide/no coincide), más 2 casos límite adicionales (JWT no aplica a revisión anónima y
     viceversa) que ya se habían verificado a mano en tareas previas pero nunca con un assert real.
   - `test_few_shot_trigger.py` — mockea `_call_llm` directamente (no `_get_client`) y confirma
     tanto el caso de éxito en el segundo intento como el de fallo en ambos, inspeccionando los
     argumentos reales con los que se llamó el mock para confirmar que el bloque de Few-Shot
     Examples está en el segundo prompt y no en el primero.

   Verificado en vivo con `pytest -v`: **26 passed, 1 skipped en 3.4s**, sin servidor levantado, sin
   Supabase real, sin gastar cuota de Gemini (todo lo externo mockeado) y sin depender de que haya
   variables de entorno reales configuradas — las que hay en `.env` se cargan igual (via
   `load_dotenv()`) pero ningún test las necesita porque nunca se llega a usarlas.

8. **Cobertura de los 4 casos identificados como faltantes** — 3 de 4 automatizados, 1 documentado
   como limitación real:
   - **Historial de 3+ niveles** ✅ — en `tests/test_api_manual.py` (caso 24, no en `tests/unit/`,
     porque necesita filas reales con `created_at` real en Supabase): crea una revisión, la
     regenera, regenera esa regeneración, y confirma que `/history` devuelve las 3 en el mismo
     orden consultando desde cualquiera de los 3 ids. Nunca se había probado con más de 2 niveles.
   - **Fallo de persistencia con LLM exitoso** ✅ — `tests/unit/test_persistence_failure.py`, con el
     test client de Flask (`create_app()` en memoria) y mockeando `analizar_codigo` +
     `review_repository.create_review`. Confirma `200` con el análisis completo y `review_id: null`,
     y confirma con `caplog` (no por inspección visual) que el log del fallo de persistencia
     efectivamente se emite.
   - **Reintentos no-429** ✅ — `tests/unit/test_llm_retries.py`, mock de un error genérico (500) que
     confirma exactamente `MAX_ATTEMPTS` llamadas antes de fallar con `LLMCommunicationError`. Antes
     solo se había verificado a mano en la auditoría original, sin ningún assert automatizado.
   - **Token realmente expirado** ⚠️ **Documentado como limitación conocida, no automatizado** —
     `tests/unit/test_expired_token.py` (test con `@pytest.mark.skip` y motivo explícito, visible en
     cualquier corrida de `pytest`). Causa real: el backend valida JWT contra el JWKS real de
     Supabase (ES256); un token "expirado" fabricado en el test con una clave propia fallaría por
     firma inválida antes de llegar a evaluarse el `exp` — eso ya lo cubre el caso 10 existente
     ("JWT inválido"), no es el mismo camino. Probar el caso real exigiría un token real emitido por
     Supabase y esperar a que expire (~1h), impráctico en un run automatizado. Se documentó la
     limitación en vez de simular un escenario que no refleja el comportamiento real, tal como pedía
     la tarea.

**Archivos nuevos de esta tarea:** `pytest.ini`, `tests/unit/test_input_processor.py`,
`tests/unit/test_response_validator.py`, `tests/unit/test_review_ownership.py`,
`tests/unit/test_few_shot_trigger.py`, `tests/unit/test_llm_retries.py`,
`tests/unit/test_persistence_failure.py`, `tests/unit/test_expired_token.py`.
**Archivos modificados:** `requirements.txt` (`pytest`), `tests/test_api_manual.py` (caso 24),
`README.md` (instrucciones de `pytest` vs. `test_api_manual.py`), este documento.
