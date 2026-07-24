# Referencia de la API — Revisor Generativo de Código

URL base (desarrollo local): `http://127.0.0.1:5000`

Documentación interactiva (para probar en vivo, con "Try it out"): `http://127.0.0.1:5000/api/docs/`
JSON crudo de la spec (OpenAPI/Swagger 2.0): `http://127.0.0.1:5000/api/openapi.json`

Este documento es la referencia completa de la API para integrar el frontend. Para setup del
backend, variables de entorno y cómo correr los tests, ver `README.md`. Para el detalle técnico
de JWT/JWKS, ver `docs/AUTH_PARA_FRONTEND.md`. Para probar cualquier endpoint en vivo desde el
navegador (incluyendo el botón "Authorize" para pegar un JWT), usar Swagger UI en
`http://127.0.0.1:5000/api/docs/` con el servidor corriendo.

---

## Qué hace el backend, en una vista rápida

Cada `POST /api/review` (o `/regenerate`) corre un pipeline completo: valida el input, arma un
prompt con guardrails educativos, se lo manda a Gemini, parsea la respuesta, y la valida contra
un Response Schema fijo (6 secciones: `summary`, `findings`, `explanation`, `suggested_code`,
`tests`, `warnings`) antes de devolverla. Si la respuesta del modelo no cumple el schema, el
backend reintenta automáticamente una vez con ejemplos de referencia adicionales en el prompt; si
ni así cumple, devuelve `503` (ver más abajo). Cada revisión (y cada regeneración) se persiste en
Supabase — ver la sección de esquema de datos más abajo.

---

## Autenticación (cómo funciona en este proyecto)

- El login lo maneja el **frontend directo con Supabase Auth** (`supabase-js`) — este backend
  nunca ve contraseñas ni implementa signup/login.
- Una vez logueado, el frontend manda el JWT de Supabase en cada request, en el header:
  ```
  Authorization: Bearer <access_token>
  ```
- **Casi todos los endpoints funcionan con o sin login** (modo anónimo vía `session_id`), excepto
  `GET /api/reviews/mine` y `GET /api/dashboard/mine`, que requieren estar logueado.
- El proyecto de Supabase usa **llaves asimétricas (ECC P-256, algoritmo ES256)** — no hay ningún
  secreto compartido. El backend valida la firma del JWT contra el JWKS público del proyecto
  (`${SUPABASE_URL}/auth/v1/.well-known/jwks.json`), sin llamar a la API de Supabase por cada
  request. Detalle completo en `docs/AUTH_PARA_FRONTEND.md`.
- ⚠️ **Importante para quien integre el frontend**: si un endpoint de auth *opcional* recibe un
  header `Authorization` mal formado (sin el prefijo `Bearer `), **no da error** — simplemente lo
  trata como anónimo, en silencio (el request "funciona" pero la revisión no queda asociada a tu
  usuario). Si el header sí trae `Bearer ` pero el token es inválido/expirado, ahí sí corta con
  `401` en cualquier endpoint de auth opcional. Hay que armar bien el header siempre:
  `Bearer ` + espacio + token.

---

## Modo anónimo (`session_id`)

Si el usuario no está logueado, el backend igual permite crear y consultar revisiones usando un
`session_id`:

- Si no lo mandás en `POST /api/review`, el backend genera uno nuevo (UUID) y te lo devuelve en
  la respuesta.
- Guardalo (ej. en `localStorage` del lado del frontend) y mandalo en los siguientes requests para
  poder consultar/regenerar/comentar esas mismas revisiones.
- Si el usuario después inicia sesión, sus revisiones anónimas previas **no se asocian
  automáticamente** a su cuenta (son conceptos separados hoy).

---

## Límites de tamaño y rate limiting

| Límite | Config (env var) | Default | Dónde aplica |
|---|---|---|---|
| Tamaño máximo del body de un request | `MAX_REQUEST_SIZE_BYTES` | 100 KB (102400 bytes) | Cualquier request con body (aplica a nivel de todo Flask, no solo a un endpoint) — si se supera, `413` |
| Caracteres máximos de `student_code` | `MAX_STUDENT_CODE_CHARS` | 20000 | `POST /api/review` y `POST /regenerate` (Input Processor) — si se supera, `400`, sin llamar al LLM |
| Rate limit por IP | `REVIEW_RATE_LIMIT` | `30 per minute` | **Solo** `POST /api/review` y `POST /api/reviews/<id>/regenerate` (los dos únicos que consumen cuota de Gemini) — si se supera, `429`. Cada uno de los dos tiene su propio contador independiente. Los endpoints de solo lectura no tienen rate limit. |

Si Gemini es el que avisa que se acabó su propia cuota, eso **hoy se traduce a `502`, no a
`429`** — un `429` que ves como cliente siempre es el rate limit propio de este backend, nunca el
de Gemini.

---

## Manejo de errores general

Además de los códigos específicos de cada endpoint (más abajo):

- **`404` genérico** (`{"error": "Recurso no encontrado."}`): cualquier ruta que no existe en la
  API (no confundir con el `404` específico de "revisión no encontrada" que sí documentan los
  endpoints de abajo, que trae un mensaje distinto).
- **`500`** (`{"error": "Error interno del servidor."}`): cualquier excepción no anticipada
  (bug). Siempre JSON, nunca HTML, sin importar la configuración de `DEBUG`.
- **`413`**: puede pasar en cualquier request con body si excede `MAX_REQUEST_SIZE_BYTES` (ver
  sección de arriba) — no es exclusivo de `/api/review`.

---

## CORS

El backend usa una lista explícita de orígenes permitidos (`ALLOWED_ORIGINS`, nunca `"*"`). Esto
solo importa si el frontend corre en un origen distinto al backend (por ejemplo, un dev server en
`http://localhost:3000` llamando a `http://127.0.0.1:5000`) — si tu frontend y tu backend
comparten origen, CORS no aplica y esta configuración no te afecta.

---

## Endpoints

### `GET /health`
Chequeo de que el servidor está vivo.
- **Auth**: no
- **Respuesta 200**: `{"status": "ok"}`

---

### `POST /api/review`
Crea una revisión de código nueva.

- **Auth**: opcional (si mandás JWT válido, la revisión queda asociada a tu usuario; rate limit
  aplica igual, esté o no autenticado)
- **Body**:

| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| `language` | string | ✅ | Ej: `"Python"` |
| `exercise` | string | ✅ | Descripción del ejercicio |
| `level` | string | ✅ | Ej: `"Basico"`, `"Intermedio"`, `"Avanzado"` (texto libre, sin validación de lista) |
| `review_type` | string | ✅ | Debe ser uno de: `Errores`, `Buenas practicas`, `Legibilidad`, `Estructura`, `Seguridad basica`, `Rendimiento`, `Pruebas sugeridas` (no distingue mayúsculas/tildes al validar) |
| `student_code` | string | ✅ | Máximo `MAX_STUDENT_CODE_CHARS` caracteres (default 20000) |
| `session_id` | string (UUID) | ❌ | Si no lo mandás, se genera uno nuevo |

- **Respuesta 200**:

```json
{
  "review_id": "uuid",
  "session_id": "uuid",
  "summary": {
    "language": "string",
    "review_type": "string",
    "overall_assessment": "string",
    "score": 0
  },
  "findings": [
    { "id": 1, "category": "Error|Improvement|Recommendation", "severity": "High|Medium|Low", "title": "string", "description": "string", "line": 1 }
  ],
  "explanation": [
    { "finding_id": 1, "why": "string", "impact": "string", "how_to_fix": "string" }
  ],
  "suggested_code": {
    "improved_code": "string",
    "changes_summary": ["string"]
  },
  "tests": [
    { "title": "string", "description": "string", "expected_result": "string" }
  ],
  "warnings": ["string"]
}
```

  `review_id` puede venir en `null` si el análisis se generó bien pero falló el guardado en
  Supabase (el resultado no se pierde igual, se devuelve completo).

- **Errores posibles**:
  - `400`: falta un campo requerido, `student_code` vacío/demasiado largo, o `review_type` fuera
    de la lista permitida
  - `401`: se mandó un `Authorization: Bearer <token>` pero es inválido o expiró (no pasa si
    directamente no se manda ningún header)
  - `413`: el request completo excede `MAX_REQUEST_SIZE_BYTES`
  - `429`: se excedió el rate limit propio de este backend (no la cuota de Gemini)
  - `502`: falló la comunicación con el modelo de IA tras los reintentos, o se excedió la cuota
    de Gemini
  - `503`: la respuesta del modelo no cumple el Response Schema ni siquiera con el reintento

---

### `GET /api/reviews/<review_id>`
Consulta una revisión puntual.

- **Auth**: depende de a quién pertenece la revisión
  - Si es de un usuario logueado → requiere el JWT de ese mismo usuario
  - Si es anónima → requiere `?session_id=<el mismo que la creó>` como query param
- **Respuesta 200**: la fila completa de la tabla `reviews` (ver esquema más abajo) — incluye
  `status`, `student_comment`, `prompt_sent`, `parent_review_id`, `created_at`, además del
  `response` con las 6 secciones de arriba.
- **Errores**: `401` (Bearer inválido/expirado), `403` (no sos el dueño — mensaje genérico, no
  revela si el id existe ni de quién es), `404` (no existe), `502` (falló la consulta a Supabase)

---

### `GET /api/reviews?session_id=<session_id>`
Historial de revisiones de una sesión anónima.

- **Auth**: no (implícita por conocer el `session_id`) — nunca requiere JWT
- **Respuesta 200**: lista de revisiones (vacía si no hay ninguna), ordenadas por fecha
  descendente
- **Errores**: `400` (falta el parámetro `session_id`), `502` (falló la consulta a Supabase)

---

### `GET /api/reviews/mine`
Historial de revisiones del usuario logueado.

- **Auth**: **obligatoria** (JWT válido)
- **Respuesta 200**: lista de revisiones del usuario, ordenadas por fecha descendente
- **Errores**: `401` (falta el token, o es inválido/expirado), `502` (falló la consulta a
  Supabase)

---

### `PATCH /api/reviews/<review_id>`
El estudiante acepta, descarta y/o comenta una revisión ya generada (revisión humana).

- **Auth**: mismo criterio de ownership que `GET /api/reviews/<id>` (JWT del dueño, o
  `session_id` correcto en el body)
- **Body** (ambos campos opcionales, mandá al menos uno):

| Campo | Tipo | Valores permitidos | Notas |
|---|---|---|---|
| `status` | string | `pending`, `accepted`, `discarded` | **Opcional.** Si se omite, el `status` actual de la revisión **no cambia** — es lo que permite implementar una acción de "solo comentar" sin alterar una decisión de aceptar/descartar ya tomada antes. No hace falta reenviar el valor actual para "no tocarlo": simplemente no incluyas la llave `status` en el body. |
| `student_comment` | string | texto libre | Opcional, independiente de `status`. |
| `session_id` | string | — | Requerido solo si la revisión es anónima (debe coincidir exactamente con el `session_id` que la creó). |

  Se requiere mandar **al menos uno** de `status`/`student_comment` (si no se manda ninguno de los
  dos, `400`). Cada uno se actualiza de forma independiente: mandar solo `student_comment` deja el
  `status` existente intacto, y viceversa — nunca se sobreescribe con un valor por defecto ni se
  infiere el que ya tenía la fila.

- **Respuesta 200**: la fila actualizada completa (mismo formato que `GET /api/reviews/<id>`)
- **Errores**: `400` (no mandaste ni `status` ni `student_comment`, o `status` no es uno de los
  valores permitidos), `401` (Bearer inválido/expirado), `403`, `404`, `413` (body demasiado
  grande — poco común acá, pero el límite es global), `502`

---

### `POST /api/reviews/<review_id>/regenerate`
Pide una nueva pasada de análisis sobre una revisión existente. Crea una fila **nueva** con
`parent_review_id` apuntando a la original — nunca la sobreescribe.

- **Auth**: mismo criterio de ownership que arriba. **Tiene el mismo rate limit por IP que
  `POST /api/review`** (contador independiente) — consume cuota de Gemini igual que crear una
  revisión nueva.
- **Body** (todos opcionales):

| Campo | Tipo | Notas |
|---|---|---|
| `session_id` | string | requerido solo si la original es anónima |
| `student_code` | string | si no se manda, reusa el código de la revisión original |
| `review_type` | string | si no se manda, reusa el `review_type` de la revisión original (que ya era válido, así que nunca falla por este motivo); si se manda uno nuevo, tiene que ser uno de los valores permitidos (misma lista que `POST /api/review`) o responde `400` |
| `motivo_regeneracion` | string | texto libre, opcional — se lo pasa a la IA como contexto de por qué se pide de nuevo |

- **Respuesta 200**: mismo formato que `POST /api/review`, más `parent_review_id` apuntando a la
  revisión original
- **Errores**: `400` (input inválido o `review_type` nuevo fuera de la lista), `401` (Bearer
  inválido/expirado), `403`, `404`, `413`, `429` (rate limit propio, no la cuota de Gemini),
  `502`, `503`

---

### `GET /api/reviews/<review_id>/history`
Devuelve toda la cadena de revisiones relacionadas (la original + todas sus regeneraciones, sin
límite de profundidad), sin importar desde cuál id de la cadena se consulte — todas se devuelven
ordenadas por fecha de creación.

- **Auth**: mismo criterio de ownership que `/regenerate`
- **Respuesta 200**: lista de filas completas, ordenadas por `created_at`
- **Errores**: `401` (Bearer inválido/expirado), `403`, `404`, `502`

---

### `GET /api/dashboard/metrics`
Métricas agregadas de **todo el sistema** (para el tablero del RF-10) — no filtra por estudiante
ni sesión.

- **Auth**: no requerida
- **Respuesta 200**:

```json
{
  "total_reviews": 0,
  "reviews_by_language": { "Python": 0, "JavaScript": 0 },
  "reviews_by_status": { "pending": 0, "accepted": 0, "discarded": 0 },
  "regenerated_count": 0,
  "most_frequent_findings": [
    { "title": "string", "count": 0 }
  ]
}
```

  - `total_reviews`: cuenta todas las filas de `reviews`, incluyendo regeneraciones.
  - `regenerated_count`: filas con `parent_review_id` no nulo.
  - `most_frequent_findings`: top 10 títulos de `findings` más repetidos en toda la tabla.

- **Error**: `503` si falla la consulta a Supabase

---

### `GET /api/dashboard/mine`
Mismas 5 métricas que `GET /api/dashboard/metrics`, pero calculadas **solo sobre las revisiones
del estudiante autenticado** — el `student_id` sale del JWT (nunca de un parámetro), así que un
usuario no puede pedir las métricas de otro.

- **Auth**: **obligatoria** (JWT válido) — a diferencia de `/metrics`, que es pública
- **Respuesta 200**: mismo formato que `GET /api/dashboard/metrics`, filtrado al usuario:

```json
{
  "total_reviews": 0,
  "reviews_by_language": { "Python": 0, "JavaScript": 0 },
  "reviews_by_status": { "pending": 0, "accepted": 0, "discarded": 0 },
  "regenerated_count": 0,
  "most_frequent_findings": [
    { "title": "string", "count": 0 }
  ]
}
```

  Si el estudiante todavía no tiene ninguna revisión propia, devuelve las 5 métricas en
  cero/vacías (no un error).

- **Errores**: `401` (falta el token, o es inválido/expirado), `503` (falló la consulta a
  Supabase)

---

## Esquema de datos (`public.reviews`)

Cada revisión (original o regeneración) es una fila de esta tabla. Las migraciones que la crean
viven en `migrations/` (se corren a mano en el SQL Editor de Supabase, el backend nunca las
ejecuta):

| Columna | Tipo | Notas |
|---|---|---|
| `id` | uuid (PK) | Generado por la base |
| `student_id` | uuid, nullable | `null` si es anónima. Referencia a `public.students` (espejo de `auth.users`, se llena sola vía trigger — el backend nunca inserta ahí a mano) |
| `session_id` | text, nullable | `null` si pertenece a un estudiante autenticado |
| `language` | text, **not null** | |
| `exercise` | text | |
| `level` | text | |
| `review_type` | text | Validado contra la lista controlada al crear/regenerar |
| `student_code` | text, **not null** | |
| `response` | jsonb, **not null** | Las 6 secciones del Response Schema |
| `parent_review_id` | uuid, nullable | `null` si es una revisión original; apunta a la anterior si es una regeneración |
| `status` | text, **not null**, default `'pending'` | `pending` \| `accepted` \| `discarded` — revisión humana (RF-08) |
| `student_comment` | text, nullable | Comentario libre del estudiante |
| `prompt_sent` | text, nullable | El prompt final completo que efectivamente se mandó al LLM para generar `response` (trazabilidad, RF-09/RNF-05) — refleja el segundo intento si hizo falta reforzar el formato |
| `created_at` | timestamptz | Default `now()` |

---

## Variables de entorno relevantes para el frontend/integración

(Lista completa y cómo levantar el backend en `README.md` — acá solo las que afectan el
contrato de la API que consume el frontend.)

| Variable | Default | Efecto sobre la API |
|---|---|---|
| `ALLOWED_ORIGINS` | (ninguno) | Orígenes permitidos por CORS, separados por coma. Nunca `"*"`. |
| `MAX_REQUEST_SIZE_BYTES` | `102400` (100 KB) | Bodies más grandes dan `413` |
| `MAX_STUDENT_CODE_CHARS` | `20000` | `student_code` más largo da `400` |
| `REVIEW_RATE_LIMIT` | `30 per minute` | Límite por IP en `/api/review` y `/regenerate` |

---

## Resumen rápido para el frontend (tabla única)

| Endpoint | Método | Auth | Rate limit | Uso típico | Errores posibles |
|---|---|---|---|---|---|
| `/health` | GET | No | No | Chequeo de vida del servidor | — |
| `/api/review` | POST | Opcional | Sí | Crear una revisión | 400, 401, 413, 429, 502, 503 |
| `/api/reviews/<id>` | GET | Según dueño | No | Ver una revisión | 401, 403, 404, 502 |
| `/api/reviews?session_id=` | GET | No | No | Historial anónimo | 400, 502 |
| `/api/reviews/mine` | GET | Sí | No | Historial del usuario logueado | 401, 502 |
| `/api/reviews/<id>` | PATCH | Según dueño | No | Aceptar/descartar/comentar | 400, 401, 403, 404, 413, 502 |
| `/api/reviews/<id>/regenerate` | POST | Según dueño | Sí | Pedir nuevo análisis | 400, 401, 403, 404, 413, 429, 502, 503 |
| `/api/reviews/<id>/history` | GET | Según dueño | No | Ver toda la cadena de regeneraciones | 401, 403, 404, 502 |
| `/api/dashboard/metrics` | GET | No | No | Datos para el tablero (global) | 503 |
| `/api/dashboard/mine` | GET | Sí | No | Datos para el tablero (solo del usuario logueado) | 401, 503 |

"Según dueño" = JWT del dueño si la revisión es de un usuario autenticado, o `session_id` exacto
si es anónima. Cualquier endpoint puede además devolver `404` genérico (ruta inexistente) o `500`
(bug no anticipado) — ver "Manejo de errores general" arriba.
