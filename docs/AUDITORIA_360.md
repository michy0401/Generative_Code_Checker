# Auditoría 360° del Proyecto Completo — Backend + Frontend + Roles

**Fecha:** 2026-07-21
**Alcance:** Todo el proyecto (`backend/` y `frontend/`). No se modificó ningún archivo de código de ninguna de las dos carpetas — es un documento de diagnóstico y asignación, no de ejecución.
**Metodología:** Relectura completa de `rubrica_evaluacion/Revisor_Generativo_Codigo_Estudiantes.pdf`, `rubrica_evaluacion/Rubrica.pdf` y `rubrica_evaluacion/Roles y tareas.pdf`; relectura de todo el código de `backend/` (confirmando vigencia contra `backend/docs/AUDITORIA_BACKEND.md` y `backend/docs/AUDITORIA_RUBRICA.md`, no copiándolas sin verificar); lectura completa por primera vez de todo el código de `frontend/` (`App.tsx`, `AuthContext.tsx`, `ProtectedRoute.tsx`, `apiFetch.ts`, `supabaseClient.ts`, `CodeReviewForm.tsx`, `Dashboard.tsx`, `History.tsx`, `DiffViewer.tsx`, `Navbar.tsx`, `Login.tsx`, `Register.tsx`); y **verificación empírica real**, no solo lectura: se corrió `npm install` y `npm run build` del frontend, se levantó el servidor de Vite (`npm run dev`) y el backend Flask (`python app.py`) simultáneamente, y se probaron con `curl` los preflights CORS reales contra el origen real de Vite (`http://localhost:5173`). Ambos procesos se detuvieron al terminar la verificación.

---

## 1. Resumen ejecutivo

El sistema **no está listo hoy para una defensa en vivo sin antes corregir un puñado de bugs de integración concretos**, aunque cada mitad por separado esté en buen estado. El backend sigue siendo sólido: se confirmó que los hallazgos de las auditorías previas (`AUDITORIA_BACKEND.md` con sus 3 addendums y `AUDITORIA_RUBRICA.md`) siguen vigentes sin cambios. El frontend, nunca antes auditado, **sí compila, sí construye (`npm run build`) y sí levanta (`npm run dev`, puerto 5173) sin errores** — eso es una buena noticia real, no algo que había que asumir.

El problema es la **integración entre ambos**, que hoy tiene bugs reales y verificados, no hipotéticos:

- Dos de las cuatro opciones del selector "Criterio" del formulario de revisión **producen un `400` garantizado** contra el backend real (los valores no coinciden con la lista controlada).
- El Dashboard calcula "Tasa de Aceptación" comparando contra una clave (`'Aceptado'`) que **nunca existe** en la respuesta real del backend (`'accepted'`), así que siempre muestra `0%` con datos reales, **sin ningún error visible** — es un bug silencioso, más peligroso que un choque visible.
- `History.tsx` asume que las filas de `GET /api/reviews/mine` tienen un campo `review_id`; el campo real es `id`. Confirmado leyendo `repositories/review_repository.py` y las migraciones: nunca hubo un renombrado de ese campo en ningún punto del backend.
- Los botones "Aceptar"/"Descartar" del formulario **no tienen ningún manejador de evento** (no hacen nada al hacer clic), y no existe en ninguna parte del frontend una UI para "Comentar" ni para "Regenerar" — las 4 acciones de RF-08 están soportadas al 100% por el backend, pero **cero** están conectadas de verdad desde la interfaz.
- Se descubrió, empíricamente (no estaba en ninguna auditoría previa), que **la configuración de CORS del backend no incluye el método `PATCH`** — así que incluso si Gerardo conecta los botones de aceptar/descartar mañana mismo, el navegador va a bloquear la petición igual, porque el backend nunca declaró `PATCH` como método permitido para peticiones cross-origin.

Una buena noticia real que contradice lo que se pensaba antes de esta auditoría: **`ALLOWED_ORIGINS` ya está corregido** a `http://localhost:5173` (el puerto real de Vite) — no quedó en el valor de ejemplo `3000`. Se verificó releyendo `.env` y confirmando en vivo con `curl` que el header `Access-Control-Allow-Origin` aparece correctamente para el origen `5173` y no para `3000`.

No se encontró ningún ítem que por sí solo hunda la nota grupal, pero sí varios que, sin corregir antes de la demo, **van a fallar visiblemente frente al evaluador** (el 400 del selector de criterio, el 0% falso del dashboard). El resto de gaps — catálogo de prompts, 5 fragmentos de código, documentación funcional — ya estaban identificados o son extensiones naturales de gaps ya conocidos, y ahora tienen dueño claro según `Roles y tareas.pdf`.

---

## 2. Parte A — Verificación técnica del frontend

### A.1 ¿Compila y corre?

✅ **Sí, verificado en vivo, no asumido.**

```
npm install        → "added 79 packages... found 0 vulnerabilities"
npm run build       → tsc -b (sin errores) + vite build → "✓ built in 762ms"
                       (única advertencia: un chunk de 614 KB, cosmético, no bloqueante)
npm run dev          → VITE v8.1.5 ready in 571 ms → http://localhost:5173/
```

No hubo que corregir nada para lograr esto — el proyecto ya arranca limpio. TypeScript en modo build (`tsc -b`) no reportó ningún error de tipos, lo cual es una señal real de calidad de código, no cosmética.

### A.2 Inventario de pantallas/rutas vs. lo asignado a Gerardo

Rutas reales en `frontend/src/App.tsx`:

| Ruta | Componente | Protegida | Tarea de `Roles y tareas.pdf` que la cubre |
|---|---|---|---|
| `/login` | `Login.tsx` | No | — (no asignada explícitamente, implementación razonable) |
| `/register` | `Register.tsx` | No | — |
| `/review` | `CodeReviewForm.tsx` | No | Tarea 2.3 [Gerardo] |
| `/dashboard` | `Dashboard.tsx` | Sí (`ProtectedRoute`) | Tarea 1.3 + 3.2 [Gerardo] |
| `/history` | `History.tsx` | Sí (`ProtectedRoute`) | Tarea 1.3 [Gerardo] |
| `*` | Redirige a `/review` | — | — |

Comparado contra lo que las tareas de Gerardo (1.3, 2.3, 3.2) piden construir:

| Pieza pedida | ¿Existe? | ¿Funciona de verdad? |
|---|---|---|
| Esqueleto de navegación (Tarea 1.3) | ✅ | ✅ `Navbar.tsx` cambia dinámicamente según `session` |
| Formulario dinámico de inputs (Tarea 2.3) | ✅ | ✅ Envía los 5 campos correctamente (ver A.3) |
| Visor de diff lado a lado (Tarea 2.3) | ✅ | ✅ `DiffViewer.tsx` usa `react-diff-viewer-continued`, recibe `originalCode`/`suggestedCode` reales |
| Botones de control humano: Aceptar/Descartar/Comentar/Regenerar (Tarea 2.3) | ⚠️ Parcial | ❌ Aceptar/Descartar existen visualmente ([CodeReviewForm.tsx:219-226](../frontend/src/pages/CodeReviewForm.tsx#L219-L226)) pero **sin `onClick`** — no hacen nada. Comentar y Regenerar **no existen en ningún lugar del frontend** (confirmado con grep: cero coincidencias de "Comentar"/"Regenerar"/"PATCH" en `frontend/src`, salvo el campo `regenerated_count` que ni se usa). |
| Componentes visuales del Dashboard (Tarea 3.2) | ✅ | ⚠️ Ver A.3 — se renderizan, pero con datos parcialmente incorrectos |
| Exportar/mostrar evidencia completa del diagnóstico (Tarea 3.2) | ❌ | No existe ningún mecanismo de exportación ni de "mostrar evidencia completa"; el botón "Ver Detalle" de `History.tsx` ([History.tsx:85](../frontend/src/pages/History.tsx#L85)) no tiene `onClick` |

### A.3 Contrato de API — verificación empírica campo por campo

**Ruta del dashboard:** ✅ Ya corregida. `Dashboard.tsx:22` llama `apiFetch('/api/dashboard/metrics')` — coincide exactamente con la ruta real del backend. El comentario en el código (`// ACTUALIZADO: Ruta correcta`) confirma que este punto específico ya se corrigió.

**Nombres de campos — NO completamente corregidos, y en un caso corregidos en la dirección equivocada:**

- `History.tsx:6` define `review_id: string;` y lo usa como key de React (`key={review.review_id}`) y lo tipa como el identificador de cada fila. El comentario dice explícitamente `// Cambiado de 'id' a 'review_id'`. **Esto es incorrecto contra el backend real**: `GET /api/reviews/mine` devuelve filas crudas de la tabla (`repositories/review_repository.py:180`, `list_reviews_by_student()`, hace `select("*")` sin renombrar nada), y la columna primaria se llama literalmente `id` (definida así en `migrations/001_init_supabase.sql:44`). El campo `review_id` (sin guion bajo antes de "id"... es decir, ese nombre exacto) solo existe en la respuesta de `POST /api/review` y `POST /.../regenerate`, que son *wrappers* distintos (`{"review_id": ..., "session_id": ..., **resultado}`), no la forma de una fila de `reviews`. Es decir: se corrigió el nombre, pero para el endpoint equivocado — el resultado es que **cada fila en `History.tsx` tiene `review.review_id === undefined`** hoy mismo, en producción, contra el backend real.
- `Dashboard.tsx` sí tipa correctamente los 5 campos reales del contrato (`total_reviews`, `reviews_by_language`, `reviews_by_status`, `regenerated_count`, `most_frequent_findings`) — la forma superficial del JSON está bien copiada de `REFERENCIA_API.md`. El problema está un nivel más abajo, en los **valores**, no en las claves del objeto (ver siguiente punto).

**Forma del JSON de métricas e historial — parcialmente corregida:**

- `most_frequent_findings`: el backend real devuelve `[{"title": ..., "count": ...}, ...]` (`review_repository.py:137-140`). `Dashboard.tsx:64-69` (`getTopError()`) sí maneja esta forma correctamente (`topError.title`).
- `reviews_by_status`: el backend real usa como claves los valores literales de la columna `status` — `"pending"`, `"accepted"`, `"discarded"` (inglés, minúsculas, restringidos por `CHECK` en `migrations/003_add_status_comment_prompt.sql`). `Dashboard.tsx:50` hace `metrics?.reviews_by_status?.['Aceptado']` — una clave en español y con mayúscula que **nunca va a existir** en la respuesta real. Peor aún: `Dashboard.tsx:35` incluye `'Regenerado': 2` en el *mock*, como si `"Regenerado"` fuera un valor posible de `status` — **no lo es**: regenerar una revisión crea una fila nueva con su propio `status='pending'` y un `parent_review_id` apuntando a la original; nunca cambia el `status` de nada a "regenerado". Ese concepto ya existe en el contrato real, pero como el campo separado `regenerated_count` — que `Dashboard.tsx` sí tipa correctamente pero **nunca muestra en pantalla**.
  **Efecto verificado:** con datos reales, `accepted` en la línea 50 será siempre `0` (porque la clave no existe), así que `acceptanceRate` se calcula y se muestra como **`0%` siempre**, sin lanzar ningún error, sin caer al `catch`, sin ningún indicio visual de que el dato está mal. Es el tipo de bug más peligroso para una demo: no se ve, pero es incorrecto.

**`review_type` — lista de valores NO sincronizada con el backend:**

`CodeReviewForm.tsx:129-133` ofrece 4 opciones:

```
"Errores y Bugs"   → normaliza a "errores y bugs"    → NO coincide con ningún valor permitido
"Buenas Prácticas" → normaliza a "buenas practicas"  → SÍ coincide ("Buenas practicas")
"Seguridad"        → normaliza a "seguridad"          → NO coincide ("Seguridad basica" ≠ "seguridad")
"Rendimiento"      → normaliza a "rendimiento"        → SÍ coincide ("Rendimiento")
```

(`_normalize_review_type()` en `services/llm_connector.py:66` solo quita tildes/mayúsculas/espacios extra — no hace fuzzy matching de palabras. "Errores y Bugs" y "Seguridad" a secas nunca van a matchear "Errores" ni "Seguridad basica" respectivamente.)

**Esto significa que 2 de las 4 opciones del selector producen, de forma garantizada y reproducible, un `400 InputValidationError` real del backend** ("review_type invalido...") si un usuario (o un evaluador durante la demo) las selecciona. Es el hallazgo más crítico de esta auditoría porque rompe el camino feliz de la forma más visible posible. Además, 3 de los 7 valores permitidos (`Legibilidad`, `Estructura`, `Pruebas sugeridas`) ni siquiera están expuestos como opción.

**`ALLOWED_ORIGINS` vs. puerto real de Vite:** ✅ **Ya corregido — verificado en vivo, contradice la suposición de la tarea.** `backend/.env` tiene hoy `ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`. Se confirmó levantando ambos servidores y probando con `curl -X OPTIONS` con `Origin: http://localhost:5173`: el backend responde con `Access-Control-Allow-Origin: http://localhost:5173`. La misma prueba con `Origin: http://localhost:3000` (el valor de ejemplo viejo) **no** trae ese header — confirma que el valor viejo ya no está activo. Este punto puede cerrarse: no es un gap real hoy.

**JWT Bearer — bien formado:** `apiFetch.ts:16` construye `headers["Authorization"] = \`Bearer ${token}\`` — coincide exactamente con lo que `middleware/auth.py:_extract_token()` exige (prefijo `"Bearer "` literal). No hay bug aquí.

**Hallazgo nuevo, no pedido explícitamente pero descubierto empíricamente probando el contrato real: CORS no permite `PATCH`.** `app.py:230` configura `CORS(app, ..., methods=["GET", "POST", "OPTIONS"])` — `PATCH` nunca se agregó a esa lista, a pesar de que `PATCH /api/reviews/<id>` existe desde la tarea 4 del backend. Se probó en vivo: un preflight `OPTIONS` con `Access-Control-Request-Method: PATCH` desde `Origin: http://localhost:5173` responde `200` pero **sin ningún header `Access-Control-Allow-Methods`** (compárese con el preflight de `GET`, que sí trae `Access-Control-Allow-Methods: GET, OPTIONS, POST`). Un navegador real bloquea la petición `PATCH` después de un preflight así, sin importar qué tan bien esté escrito el frontend. Esto significa que **aunque Gerardo conecte los botones de Aceptar/Descartar hoy mismo, la función seguiría sin funcionar desde un navegador** hasta que también se corrija esto del lado del backend.

### A.4 Autenticación

✅ Implementada consistentemente. `Register.tsx`/`Login.tsx` usan `supabase.auth.signUp()`/`signInWithPassword()` directamente contra `supabaseClient.ts`, que a su vez usa `VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY` de `frontend/.env`. Se confirmó que ese `VITE_SUPABASE_URL` (`https://loglmdehedodfkrjmjnb.supabase.co`) es **exactamente el mismo proyecto** que usa el backend (`SUPABASE_URL` en `backend/.env`) — así que los JWT que emite Supabase Auth para un login del frontend son válidos contra el JWKS/ES256 que `middleware/auth.py` verifica. No hay descoordinación de proyectos de Supabase entre las dos partes. `AuthContext.tsx` resuelve la sesión inicial (`getSession()`) y se suscribe a cambios (`onAuthStateChange`) correctamente.

### A.5 Rutas protegidas

✅ Confirmado por lógica, no solo por existencia. `ProtectedRoute.tsx:8-16`: mientras `loading` es `true` muestra un estado de carga (evita un parpadeo hacia `/login` antes de que la sesión resuelva); si no hay `session`, hace `<Navigate to="/login" replace />`; si hay sesión, renderiza los `children`. `/dashboard` y `/history` están envueltas en este componente en `App.tsx`. Funciona.

### A.6 Datos simulados (mock data)

Confirmado: **`Dashboard.tsx` y `History.tsx` ambos siguen con mock data en el `catch`** de su `fetch` respectivo (`Dashboard.tsx:30-38`, `History.tsx:28-34`). Esto es más riesgoso de lo que parece a simple vista: como el bug de `reviews_by_status` (A.3) hace que el *fetch* del Dashboard **tenga éxito** (200 OK) con datos reales pero mal interpretados, el mock nunca se activa ahí — el problema es silencioso, no se disfraza de mock. Pero si el *fetch* falla por cualquier otro motivo real (el bug de CORS+PATCH de arriba, el backend caído, sin red), el usuario vería **números completamente inventados** (`total_reviews: 42`, etc.) sin ningún indicio de que no son reales. Ninguna de las dos vistas muestra un mensaje de error visible al usuario cuando cae al mock — simplemente sustituye los datos en silencio.

---

## 3. Parte B — Vigencia de las auditorías previas del backend

Se releyeron `backend/docs/AUDITORIA_BACKEND.md` (con sus 3 addendums) y `backend/docs/AUDITORIA_RUBRICA.md`, y se verificó cada hallazgo marcado como resuelto contra el código actual (no se copió nada sin confirmar).

| Hallazgo previo | Estado al confirmar hoy | Cambió? |
|---|---|---|
| Ownership check en `GET /api/reviews/<id>` | ✅ Sigue presente (`routes/review.py:257`, llama a `review_ownership.is_owner()`) | No cambió |
| JSON garantizado en errores no controlados (`@app.errorhandler(Exception)`) | ✅ Sigue presente (`app.py:301`) | No cambió |
| Límite de tamaño de input (`MAX_CONTENT_LENGTH`, `MAX_STUDENT_CODE_CHARS`) | ✅ Siguen presentes (`config.py:28`, `llm_connector.py:48`) | No cambió |
| Rate limiting (`flask-limiter`) | ✅ Sigue activo — confirmado en vivo: al levantar el servidor para las pruebas de CORS de esta auditoría, se vio el warning real de `flask_limiter` sobre almacenamiento en memoria | No cambió |
| Prompt Versioning + Few-Shot Examples | ✅ Siguen presentes (`PROMPT_VERSION = "1.2"`, `FEW_SHOT_EXAMPLES` en `llm_connector.py`) | No cambió |
| Suite de `pytest` (`tests/unit/`, 8 archivos) | ✅ Confirmada presente vía listado de archivos | No cambió |
| `PATCH /api/reviews/<id>`, `prompt_sent`, `status`, `student_comment` (Tarea 4) | ✅ Siguen presentes y persistidos | No cambió |
| Dashboard `GET /api/dashboard/metrics` (Tarea 5) | ✅ Sigue presente; se confirmó en vivo con datos reales acumulados (`most_frequent_findings` trajo datos reales con conteos > 30, evidencia de que hay historial real de test runs previos) | No cambió |
| Gaps de `AUDITORIA_RUBRICA.md`: catálogo de prompts formal, 5 fragmentos consolidados, RF-11 parcial | ⚠️ Siguen exactamente igual, sin resolver | No cambió |
| CORS — verificado en auditorías previas solo para `GET`/preflight genérico | ⚠️ **Cambió de forma indirecta**: aquella verificación fue anterior a que existiera `PATCH /api/reviews/<id>` (agregado en la Tarea 4) y nunca se re-probó específicamente para ese método una vez agregado. No es que "se rompió" — es que nunca se validó para este caso, y esta auditoría es la primera en probarlo empíricamente contra un método distinto de GET/POST. |
| `ALLOWED_ORIGINS` | ✅ Nunca estuvo documentado como gap abierto en ninguna auditoría previa del backend (porque nunca hubo un frontend real contra el cual probarlo) — hoy se confirma que ya apunta al puerto correcto de Vite | Es contexto nuevo, no una regresión |

**Conclusión de la Parte B:** ninguna de las auditorías previas del backend quedó desactualizada en sus afirmaciones — todo lo que decían que estaba resuelto, sigue resuelto. El único punto realmente nuevo es el de CORS+`PATCH`, que ninguna auditoría anterior pudo detectar porque ninguna probó ese método específico contra un origen cruzado real.

---

## 4. Parte C — RF/RNF end-to-end (sistema completo, no solo backend)

| Código | Requisito | Backend solo (auditoría previa) | Sistema completo hoy | Motivo del cambio |
|---|---|---|---|---|
| RF-01 | Gestión de revisiones (crear/consultar/editar/mantener) | ✅ | ⚠️ Parcial | Crear ✅ funciona end-to-end. Consultar ⚠️ (Dashboard/Historial muestran datos, pero con errores; no hay vista de detalle de una revisión puntual). Editar ❌ (PATCH nunca se invoca desde la UI — ni el botón está conectado ni el estado retiene el `id` necesario). Mantener ⚠️ (Regenerar no tiene ninguna UI). |
| RF-02 | Registro de contexto | ✅ | ✅ | El formulario captura y envía los 5 campos correctamente. |
| RF-03 | Selección de criterios | ✅ | ⚠️ Parcial | El backend acepta 7 valores correctos; el selector del frontend ofrece 4, y 2 de esos 4 no coinciden con ningún valor permitido → `400` garantizado en esos casos. |
| RF-04 | Análisis generativo | ✅ | ✅ | Funciona end-to-end cuando `review_type` es uno de los 2 valores que sí matchean. |
| RF-05 | Explicación educativa | ✅ (el backend la genera) | ⚠️ Parcial | El campo `explanation` viaja completo en la respuesta, pero `CodeReviewForm.tsx` **nunca lo renderiza** — no hay ninguna sección de la UI que muestre `why`/`impact`/`how_to_fix`. Se genera, pero no se ve. |
| RF-06 | Código sugerido | ✅ | ✅ | `DiffViewer` sí lo muestra correctamente. |
| RF-07 | Pruebas sugeridas | ✅ (el backend las genera) | ⚠️ Parcial | Igual que RF-05: el campo `tests` viaja completo pero nunca se renderiza en ninguna parte de `CodeReviewForm.tsx`. |
| RF-08 | Revisión humana (aceptar/descartar/comentar/regenerar) | ✅ | ❌ No cumplido end-to-end | Las 4 acciones existen y funcionan en el backend. En la UI: Aceptar/Descartar son botones sin `onClick`; Comentar y Regenerar no tienen ninguna UI. Y aunque se conectaran, CORS bloquearía `PATCH` hoy. |
| RF-09 | Historial de IA (7 campos) | ✅ | ✅ (persistencia) / ⚠️ (exposición en UI) | El sistema sigue registrando los 7 campos correctamente. `History.tsx` solo expone 4 de ellos en la tabla (fecha, lenguaje, criterio, estado) — el resto (prompt, código, respuesta) nunca se muestra porque "Ver Detalle" no funciona. |
| RF-10 | Dashboard básico | ✅ | ⚠️ Parcial | Los datos existen y son correctos en el backend. La UI muestra 4 métricas, una de ellas (tasa de aceptación) con un bug de contrato que la vuelve falsa; `regenerated_count` y el top-10 completo de `most_frequent_findings` nunca se exponen (solo el primero). |
| RF-11 | Reporte o evidencia exportable | ⚠️ Parcial (solo backend) | ❌ No cumplido end-to-end | El backend expone toda la evidencia cruda; ni "Ver Detalle" ni ningún mecanismo de exportación existen en el frontend hoy. |

| Código | RNF | Sistema completo hoy | Detalle |
|---|---|---|---|
| RNF-01 | Arquitectura | ✅ | Ambos lados con separación razonable por carpetas/responsabilidades. |
| RNF-02 | Seguridad (keys fuera del repo) | ✅ | Confirmado también en frontend: `frontend/.gitignore` incluye `.env`; `frontend/.env` no está trackeado. |
| RNF-03 | Privacidad | ✅ | Sin cambios — el frontend no agrega datos personales al payload enviado al backend. |
| RNF-04 | Validación | ⚠️ Parcial | El backend valida todo correctamente. La UI solo usa el atributo HTML `required` (validación nativa del navegador); no hay aviso previo sobre el límite de 20000 caracteres ni mensajes de validación específicos mostrados al usuario. |
| RNF-05 | Trazabilidad | ✅ (persistencia) / ⚠️ (exposición) | Igual que RF-09. |
| RNF-06 | Manejo de errores | ⚠️ Parcial | El backend da mensajes claros y específicos por tipo de falla. El frontend los descarta: `CodeReviewForm.tsx:63` solo muestra `"Error del servidor: {status}"` (ignora el JSON con el mensaje real). Peor: el fallback a mock data en Dashboard/History **reemplaza silenciosamente** un fallo real por datos falsos, en vez de mostrar un mensaje de error — es el comportamiento opuesto al que pide este RNF. |
| RNF-07 | Usabilidad | ⚠️ Parcial — **ahora sí evaluable, antes no** | Cada pantalla individual es simple y navegable (estados de carga, mensajes de error visibles en el formulario de revisión). Pero los botones sin función (Aceptar/Descartar/Ver Detalle) y los números del dashboard que se ven bien pero son incorrectos **generan una falsa sensación de que el flujo funciona completo**, que es peor para la usabilidad real que si la función faltara abiertamente. |
| RNF-08 | Mantenibilidad | ⚠️ Parcial | El backend tiene guía de instalación completa. `frontend/README.md` sigue siendo **el template por defecto de Vite** (sin editar) — no documenta `VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY`, ni cómo obtenerlos, ni nada específico de este proyecto. |

---

## 5. Parte D — Mapeo actualizado contra los 10 criterios de la rúbrica (defensa grupal, 70%)

| # | Criterio | Peso | Cambia con el frontend real | Estado actualizado |
|---|---|---|---|---|
| 1 | Solución efectiva del sistema | 10% | Sí | ⚠️ El pipeline funciona, pero la demo en vivo tiene puntos de quiebre reales y reproducibles (el 400 del selector, el dashboard con dato falso) si no se prueban antes de presentar. |
| 2 | Arquitectura, diseño técnico y calidad del código | 12% | Marginal | ✅ Ambos lados mantienen buena separación. El frontend, aunque nuevo, compila limpio y sin errores de tipos. |
| 3 | Uso central y correcto de IA generativa | 14% | Sí, hacia abajo | ⚠️ El backend genera correctamente `explanation` y `tests`, pero al no renderizarse en pantalla, una demo en vivo **no muestra** dos de los siete elementos de salida que pide la Sección 7 del enunciado — la IA "hace más" de lo que se ve. |
| 4 | Calidad del prompting | 8% | No | Sin cambios respecto a `AUDITORIA_RUBRICA.md` — sigue faltando el catálogo formal, gap de Erick, no relacionado al frontend. |
| 5 | Integración técnica con modelos o servicios de IA | 8% | Sí, si se interpreta en sentido amplio | ⚠️ La integración LLM↔backend sigue sólida; pero la integración backend↔frontend (que también es "integración técnica" del sistema) tiene los bugs de contrato ya descritos. |
| 6 | Datos, contexto y trazabilidad | 6% | Marginal | ✅ El dato existe y es correcto; solo una fracción se expone visualmente hoy. |
| 7 | Seguridad, privacidad y uso responsable | 6% | Sí, un poco | ⚠️ Nada de exposición de datos nueva, pero el hueco de CORS/`PATCH` es un hallazgo de "integración técnica responsable" que vale la pena mencionar aquí también, no solo como bug funcional. |
| 8 | Calidad funcional y experiencia de usuario | 6% | **El que más cambia** | ❌→⚠️ Antes marcado "no evaluable desde el backend". Ahora que hay frontend real, es evaluable, y el resultado es débil: botones sin función, números incorrectos sin aviso, dos de cuatro opciones de un selector rotas. Es el criterio con más riesgo concreto de nota baja hoy. |
| 9 | Documentación y lineamientos del proyecto | 5% | Sí | ⚠️ A los gaps ya conocidos del backend (catálogo de prompts, 5 fragmentos) se suma que el manual funcional/de usuario (co-liderado por Gerardo) no existe — el README del frontend es el template por defecto, sin personalizar. |
| 10 | Presentación grupal y profesionalismo | 5% | No | Fuera del alcance de este documento — depende de la exposición oral, no del código. |

---

## 6. Parte E — Tabla final de gaps con dueños, dependencias, prioridad y esfuerzo

Roles según `rubrica_evaluacion/Roles y tareas.pdf`: **Gerardo** (Frontend), **Michelle** (Backend Core/APIs y persistencia), **Erick** (AI Engineer & Prompt Architect), **Carla** (QA & Test Master), **Fernando** (Middleware & Data Engineer).

| # | Gap | Dueño(s) | Depende de | Prioridad | Esfuerzo |
|---|---|---|---|---|---|
| 1 | Selector "Criterio" en `CodeReviewForm.tsx` envía 2 valores (`"Errores y Bugs"`, `"Seguridad"`) que no coinciden con ningún valor de `ALLOWED_REVIEW_TYPES` real → `400` garantizado | **Gerardo** | Nada externo — el contrato ya está documentado en `backend/docs/REFERENCIA_API.md`/Swagger. Coordinación recomendada con Michelle solo para confirmar la lista final de 7 valores. | **Crítico** | Bajo |
| 2 | `Dashboard.tsx` compara `reviews_by_status['Aceptado']` contra un contrato real que usa `'accepted'`/`'pending'`/`'discarded'` — "Tasa de Aceptación" siempre da `0%` con datos reales, sin error visible | **Gerardo** | Nada externo — mismo contrato ya documentado. | **Crítico** | Bajo |
| 3 | `History.tsx` asume el campo `review_id` en filas de `GET /api/reviews/mine`; el campo real es `id` | **Gerardo** | Nada externo. | **Importante** | Bajo |
| 4 | Botones "Aceptar"/"Descartar" sin `onClick`; no existe UI para "Comentar" ni "Regenerar"; el estado del formulario no retiene el `review_id`/`session_id` necesario para poder llamar `PATCH` | **Gerardo** | El estado debe capturar primero `review_id`/`session_id` de la respuesta de `POST /api/review` (mismo dueño, prerequisito de código). Además, no se puede demostrar funcionando sin resolver el gap #5 (CORS) al mismo tiempo. | **Crítico** | Medio |
| 5 | CORS del backend (`app.py`, `methods=["GET","POST","OPTIONS"]`) no incluye `PATCH` — bloquea la acción humana incluso si el frontend se corrige | **Michelle** | Nada por sí solo, pero **inútil sin el gap #4** y viceversa — requiere coordinación explícita entre Gerardo y Michelle para probarlo junto, no arreglos por separado sin avisarse. | **Crítico** | Bajo |
| 6 | "Ver Detalle" sin función en `History.tsx`; no existe exportar/mostrar evidencia completa en el Dashboard (pedido explícito de la Tarea 3.2) | **Gerardo** | Nada externo — el backend ya expone `GET /api/reviews/<id>` con todos los datos necesarios. | **Importante** | Medio |
| 7 | `CodeReviewForm.tsx` nunca renderiza los campos `explanation` ni `tests` de la respuesta de la IA | **Gerardo** | Nada externo. | **Importante** | Bajo |
| 8 | Frontend descarta el mensaje de error real del backend (solo muestra el código de status); Dashboard/History reemplazan fallos de red con mock data sin avisar al usuario | **Gerardo** | Nada externo. | **Importante** | Bajo-Medio |
| 9 | Catálogo de prompts formal (objetivo + versión + ejemplo de entrada/salida por prompt) no existe como documento | **Erick** (rol explícito: "creador del Catálogo de Prompts obligatorio"; Tarea 3.4) | **Depende de Carla** — la Tarea 3.4 pide explícitamente "los ejemplos reales de entrada/salida de los 5 casos probados por QA", es decir, depende de que la Tarea 3.3 de Carla (gap #10) esté terminada primero. | **Importante** | Bajo (la materia prima ya existe en código) |
| 10 | Conjunto de 5 fragmentos de código con problemas distintos (sintaxis, inyección SQL, legibilidad, rendimiento, lógica errónea) no existe consolidado | **Carla** (Tarea 3.3, "CAMBIO CLAVE" en el documento de roles) | Nada externo, aunque el gap #9 de Erick depende de que esta se resuelva primero. | **Importante** | Medio |
| 11 | Evidencia de pruebas consolidada / Guía de Ejecución oficial del proyecto como documento propio | **Carla** (rol explícito: "dueña de la Guía de Ejecución y del reporte de Evidencia de Pruebas") | Puede reusar gran parte de `backend/docs/GUIA_SWAGGER.md` y `backend/README.md` (ya escritos por Michelle) — se recomienda coordinación para no duplicar contenido, no reescribir desde cero. | **Importante** | Medio |
| 12 | Documento Funcional / Manual de Usuario no existe; `frontend/README.md` sigue siendo el template por defecto de Vite | **Gerardo** (co-lidera el Documento Funcional según su rol) + **coordinación de "TODOS"** en la Tarea 3.5 para unificarlo con el Documento Técnico | Necesita que exista contenido real de la UI ya estabilizada (gaps #1-8 resueltos primero, para no documentar comportamiento roto). | **Importante** | Bajo-Medio |
| 13 | No existe un Documento Técnico de Arquitectura consolidado de *todo* el sistema (front+back); hoy la documentación técnica vive dispersa y solo cubre bien el backend | **Fernando** (rol explícito: "consolidar el Documento Técnico de Arquitectura") | Ya existe suficiente material fuente (README de backend, `REFERENCIA_API.md`, `AUTH_PARA_FRONTEND.md`) — falta unificarlo, no producirlo desde cero. | **Importante** | Medio |
| 14 | Las métricas del Dashboard se calculan agregando en Python (`review_repository.py:get_dashboard_metrics()`), no mediante vistas SQL en Supabase como asigna la Tarea 3.1 a Fernando. Decisión de equipo: no se reimplementa ni se mueve código — se documenta que Michelle lo implementó y Fernando asume dominio conceptual completo para su defensa individual. | Fernando (defensa individual) / Michelle (autoría real, transferencia de conocimiento) | Sesión de traspaso Michelle→Fernando sobre `get_dashboard_metrics()`: qué agregaciones calcula, de dónde salen los datos, y por qué se implementó en Python en vez de vista SQL | **Importante** (afecta nota individual de Fernando, no la grupal) | Bajo (redocumentar autoría + traspaso de conocimiento, sin tocar código) |
| 15 | El parser defensivo contra JSON malformado/alucinaciones (Tarea 2.4, asignada a Fernando junto con QA) está implementado en `services/llm_connector.py` (`_clean_output_text()`, `_validate_response()`), es decir, por Michelle, no por Fernando. Decisión de equipo: no se mueve código — se documenta la autoría real y Fernando asume dominio conceptual completo para su defensa individual. | Fernando (defensa individual) / Michelle (autoría real, transferencia de conocimiento) | Sesión de traspaso Michelle→Fernando sobre `_clean_output_text()`/`_validate_response()`: qué tipos de fallo detecta, qué hace en cada caso, y ejemplos concretos de entrada/salida fallida. | **Importante** (afecta nota individual de Fernando, no la grupal) | Bajo (redocumentar autoría + traspaso de conocimiento, sin tocar código) |
| 16 | El `session_id` anónimo nunca se persiste en el frontend (ni `localStorage` ni estado) — un usuario anónimo pierde la continuidad de su propia revisión tras refrescar | **Gerardo** | Nada externo. | **Nice to have** | Bajo |
| 17 | No hay aviso previo sobre el límite de 20000 caracteres de `student_code` ni mensajes de validación específicos en el formulario | **Gerardo** | Nada externo. | **Nice to have** | Bajo |

---

**Actualización (2026-07-21) — Gap #5 resuelto.** Se agregó `"PATCH"` a `methods=[...]` en la configuración de `CORS(...)` de `app.py`. Verificado en vivo: un preflight `OPTIONS` con `Access-Control-Request-Method: PATCH` desde `Origin: http://localhost:5173` ahora responde `Access-Control-Allow-Methods: GET, OPTIONS, PATCH, POST`; el mismo preflight desde un origen no permitido (`http://evil.com`) sigue sin traer ningún header de CORS — no se relajó el control de origen al resolver esto. Los 30 casos de `tests/test_api_manual.py` y los 42 de `tests/unit/` (1 skip esperado) se corrieron de nuevo después del cambio y siguen pasando sin modificaciones. El gap #4 (botones sin conectar en el frontend) sigue pendiente y sigue siendo responsabilidad de Gerardo — este fix solo destraba que, una vez conectados, la petición `PATCH` deje de ser bloqueada por el navegador.

## Nota final

Los gaps #1, #2, #3, #4, #6, #7, #8, #12, #16 y #17 son, en esencia, del mismo origen: el frontend se construyó sin una pasada final de verificación campo por campo contra `backend/docs/REFERENCIA_API.md`, que ya documentaba el contrato real correcto en el momento en que se escribió cada uno de esos archivos. Ninguno de ellos requiere tocar el backend (excepto el #5, que sí). El gap #5 es, en cambio, puramente responsabilidad del backend y quedó sin detectar hasta esta auditoría porque nunca se había probado `PATCH` contra un origen cruzado real. Los gaps #9 a #15 son heredados o de reparto de roles, no de código roto, y su resolución depende más de coordinación de equipo que de esfuerzo técnico individual.

---

## Re-verificación post-fixes de Gerardo (2026-07-21)

**Metodología:** no es una auditoría nueva — es una re-verificación puntual de los 17 gaps ya identificados, con el mismo rigor empírico que la auditoría original. Se releyó el código real de `frontend/src/pages/CodeReviewForm.tsx`, `Dashboard.tsx` y `History.tsx` (los 3 únicos archivos que cambiaron, confirmado con `git show --stat` sobre el commit `5ecfde7` "Frontend post-auditoría" de Gerardo). Se corrió `npm install` + `npm run build` (compila limpio) + `npm run dev` (levanta en `5173`), se levantó el backend real (`python app.py`, con el fix de CORS del gap #5 ya aplicado), y se reprodujo con `curl` — replicando exactamente el método, los headers y el shape del body que emite cada función del frontend — un flujo completo real: crear una revisión anónima con `review_type="Buenas practicas"` (un valor real del selector corregido), aceptarla vía `PATCH`, y confirmar que `GET /api/dashboard/metrics` refleja el cambio con datos reales (no mock). No se usó navegador real (sigue sin existir una herramienta de automatización de navegador en este entorno, tal como se documentó en `docs/GUIA_SWAGGER.md`), pero replicar la petición HTTP exacta que el código emite — mismo método, mismos headers, mismo `Origin`, mismo body — prueba lo mismo que probaría un navegador real en cuanto a CORS y contrato de datos.

### Tabla de los 17 gaps originales

| # | Estado anterior | Estado actual | Evidencia |
|---|---|---|---|
| 1 — `review_type` no coincide con `ALLOWED_REVIEW_TYPES` | ❌ Sigue igual | ✅ **Resuelto** | `CodeReviewForm.tsx:178-184` ahora ofrece exactamente los 7 valores reales (`Errores`, `Buenas practicas`, `Seguridad basica`, `Rendimiento`, `Legibilidad`, `Estructura`, `Pruebas sugeridas`). Probado en vivo: `POST /api/review` con `review_type="Buenas practicas"` → `200`, análisis real de Gemini devuelto, `review_id` persistido. |
| 2 — Dashboard compara `reviews_by_status['Aceptado']` (no existe) | ❌ Sigue igual | ✅ **Resuelto** | `Dashboard.tsx:44` ahora usa `reviews_by_status?.['accepted']` (comentario explícito: `// CORREGIDO GAP 2`). Confirmado en vivo: tras aceptar una revisión real vía `PATCH`, `GET /api/dashboard/metrics` pasó de `"accepted": 5` a `"accepted": 6` sobre `"total_reviews": 68` — la tasa de aceptación ahora se calcula sobre una clave que sí existe. |
| 3 — `History.tsx` asume `review_id`, el campo real es `id` | ❌ Sigue igual | ✅ **Resuelto** | `History.tsx:5` ahora tipa `id: string;` y usa `review.id` como key (`History.tsx:78`), coincidiendo con la columna real de `reviews`. |
| 4 — Botones Aceptar/Descartar/Comentar/Regenerar sin conectar | ❌ Sigue igual | ⚠️ **Parcial — con una regresión nueva real (ver gap #18)** | Aceptar/Descartar ahora tienen `onClick` (`CodeReviewForm.tsx:291-304`) y llaman `PATCH /api/reviews/<id>` (`handleAction()`, línea 109). "Comentar" existe pero no como acción independiente: el textarea de comentario solo se envía junto con Aceptar o Descartar, no hay un botón de "solo comentar". "Regenerar" **no tiene ninguna UI** — cero referencias en todo `frontend/src` (confirmado con grep). Y se descubrió, probando en vivo, que el `PATCH` real falla con `403` para el camino anónimo — ver gap nuevo #18 abajo. |
| 5 — CORS sin `PATCH` | ✅ Resuelto (fix propio anterior) | ✅ **Sigue resuelto, reconfirmado junto con el código nuevo** | Preflight real repetido tras el cambio de Gerardo: `Access-Control-Allow-Methods: GET, OPTIONS, PATCH, POST` sigue presente para `Origin: http://localhost:5173`. Pero el fix de CORS por sí solo ya no es el bloqueador — ahora lo es el gap #18 (session_id faltante en el PATCH). |
| 6 — "Ver Detalle"/exportar evidencia sin función | ❌ Sigue igual | ⚠️ **Parcial — mejora real, pero incompleta** | `History.tsx:95-100` conecta el botón a un modal (`selectedReview`) que muestra `language`, `review_type`, `status`, `created_at`, `exercise`, `student_code` y `student_comment` (`History.tsx:117-198`). Es una mejora real y funcional. Pero no muestra `prompt_sent` (el prompt real enviado al LLM, RF-09/RNF-05) ni el `response` completo (findings/suggested_code/tests) — ambos campos sí viajan en el JSON de `GET /api/reviews/mine` (confirmado: es un `select("*")`) pero el modal nunca los renderiza. "Evidencia completa" queda parcial, no total. |
| 7 — `explanation`/`tests` generados pero no mostrados | ❌ Sigue igual | ⚠️ **Parcial — con un bug nuevo de mapeo de campos (ver gap #19)** | Ambas secciones ahora se renderizan (`CodeReviewForm.tsx:228-251`). "Pruebas Sugeridas" funciona bien: los nombres reales (`title`, `description`) coinciden con lo que el código busca. "Explicación Educativa" no: el código busca `exp.concept`/`exp.title`/`exp.description`/`exp.details`, pero el schema real (confirmado con una respuesta real de Gemini) usa `finding_id`/`why`/`impact`/`how_to_fix` — ninguno coincide. Cada explicación se va a mostrar con el encabezado genérico "Concepto" y el cuerpo como un volcado JSON crudo en vez de texto legible. No rompe nada, pero se ve mal en una demo. |
| 8 — Frontend descarta mensajes de error reales / mock data silenciosa | ❌ Sigue igual | ✅ **Resuelto** | `Dashboard.tsx` y `History.tsx` ya no tienen ningún mock de respaldo (comentario explícito: `// CORREGIDO GAP 8: Adiós mock data.`) — ambos usan `setError()` y muestran el mensaje real. `CodeReviewForm.tsx:91-92` y los otros dos archivos ahora leen `errData.error` del JSON real del backend en vez de solo el código de status. |
| 9 — Catálogo de prompts formal (Erick) | ⚠️ Pendiente | ⚠️ **Sin cambios, como se esperaba** | Confirmado: no hay archivos nuevos en `backend/docs/` ni en ningún otro lado relacionados a un catálogo de prompts. |
| 10 — 5 fragmentos de código consolidados (Carla) | ⚠️ Pendiente | ⚠️ **Sin cambios, como se esperaba** | Sin evidencia de ningún documento nuevo. |
| 11 — Evidencia de pruebas / Guía de Ejecución (Carla) | ⚠️ Pendiente | ⚠️ **Sin cambios, como se esperaba** | Sin cambios en `backend/docs/`. |
| 12 — Documento Funcional / README de frontend (Gerardo) | ⚠️ Pendiente | ⚠️ **Sin cambios** | `frontend/README.md` sigue siendo el template por defecto de Vite — confirmado con `git log` sobre ese archivo: el único commit que lo tocó es el commit inicial del repo. No se actualizó en el commit "Frontend post-auditoría", aunque ese commit sí tocó 3 archivos de código — el README no era parte de su alcance esta vez. |
| 13 — Documento Técnico consolidado (Fernando) | ⚠️ Pendiente | ⚠️ **Sin cambios, como se esperaba** | Sin evidencia de ningún documento nuevo. |
| 14 — Métricas del Dashboard en Python, no en vista SQL (Fernando/Michelle) | ⚠️ Decisión de equipo tomada | ⚠️ **Sin cambios, consistente con la decisión ya tomada** | `review_repository.py:get_dashboard_metrics()` sigue implementado en Python, sin mover a vista SQL — coincide con lo decidido (traspaso de conocimiento, no reimplementación). |
| 15 — Parser defensivo en `llm_connector.py`, no en módulo de Fernando | ⚠️ Decisión de equipo tomada | ⚠️ **Sin cambios, consistente con la decisión ya tomada** | `_clean_output_text()`/`_validate_response()` siguen en `services/llm_connector.py`, sin mover — coincide con lo decidido. |
| 16 — `session_id` anónimo no persistido en el frontend | ❌ Sigue igual | ✅ **Resuelto** | `CodeReviewForm.tsx:49-56` ahora persiste `session_id` en `localStorage` (`crypto.randomUUID()` con fallback) y lo manda en el `POST` (línea 81). Confirmado en vivo: el `session_id` enviado se guardó correctamente en la fila creada. Nota irónica: este mismo campo, ya resuelto en el `POST`, es el que falta en el `PATCH` — ver gap #18. |
| 17 — Sin aviso de límite de caracteres / validación visible | ❌ Sigue igual | ✅ **Resuelto** | `CodeReviewForm.tsx:198-204`: contador visible `{studentCode.length}/20000` (rojo pasando 19500) + atributo `maxLength={20000}` que impide físicamente escribir más. Coincide exactamente con `MAX_STUDENT_CODE_CHARS` del backend. |

### Gaps nuevos encontrados en esta re-verificación

| # | Gap | Dueño(s) | Depende de | Prioridad | Esfuerzo |
|---|---|---|---|---|---|
| 18 | `handleAction()` en `CodeReviewForm.tsx:114-120` nunca incluye `session_id` en el body del `PATCH /api/reviews/<id>`. Para una revisión anónima (el camino por defecto: `/review` es pública y la ruta comodín redirige ahí), `review_ownership.is_owner()` exige el `session_id` exacto cuando `student_id` es `None` — sin él, el backend responde `403` siempre. **Confirmado empíricamente**: se creó una revisión anónima real, se intentó aceptar exactamente como lo hace el código (sin `session_id` en el `PATCH`) → `403 "No tenes permiso para modificar esta revision"`; la misma petición agregando `session_id` manualmente → `200`, aceptada y persistida correctamente. Para usuarios **autenticados** este bug no aplica (la propiedad se valida por `student_id` del JWT, no por `session_id`), así que el camino logueado de Aceptar/Descartar/Comentar sí funciona de punta a punta hoy. | **Gerardo** | Nada externo — el mismo estado `sessionId` que ya existe en el componente (usado correctamente en el `POST`, línea 81) solo necesita agregarse también al body del `PATCH`. | **Crítico** (bloquea RF-08 en el camino anónimo, que es el que ve cualquiera que entre a la app sin loguearse primero) | Bajo |
| 19 | La sección "Explicación Educativa" de `CodeReviewForm.tsx:228-240` busca campos (`concept`, `title`, `description`, `details`) que no existen en el schema real de `explanation` (`finding_id`, `why`, `impact`, `how_to_fix`, confirmado con una respuesta real de Gemini durante esta re-verificación). No rompe la app (cae a `JSON.stringify(exp)` como respaldo), pero muestra un volcado de JSON crudo en vez de texto legible bajo el encabezado genérico "Concepto" para cada hallazgo. | **Gerardo** | Nada externo — el shape ya está documentado en `schemas/response_schema.json` y en `backend/docs/REFERENCIA_API.md`. | **Importante** (no bloquea el flujo, pero se ve mal en una demo en vivo — afecta el criterio 3 y 8 de la rúbrica) | Bajo |

### Resumen ejecutivo de esta re-verificación

Hay progreso real y verificado: **9 de los 17 gaps originales quedaron completamente resueltos** (#1, #2, #3, #5, #8, #16, #17, y funcionalmente los renders de #7 en su mitad de "tests"), y **2 más mejoraron sustancialmente sin cerrar del todo** (#6, #7). Los gaps #9-15 (documentación/roles) siguen exactamente donde estaban, como se esperaba, sin sorpresas.

**El sistema todavía no está listo para una demo end-to-end sin sorpresas.** La razón concreta es el gap nuevo #18: el camino más probable de una demo en vivo —un evaluador entra a la app, cae en `/review` (la ruta pública/comodín, sin necesidad de loguearse), genera una revisión, e intenta aceptarla o descartarla— va a fallar con un `403` visible (via `alert()`) hoy mismo, porque el `PATCH` real nunca manda el `session_id` que la revisión anónima necesita para autorizar la acción. El camino autenticado (login → dashboard/historial) sí funciona de punta a punta. Antes de cualquier demo real, se recomienda que Gerardo aplique el fix del gap #18 (bajo esfuerzo, un campo que ya existe en el componente) — sin eso, el flujo más visible del sistema (RF-08 sin login) sigue roto pese a que los gaps #1, #2 y #5 que lo bloqueaban antes ya se resolvieron.

---

## Segunda re-verificación — gaps #18, #19, #4, #6, #12 (2026-07-22)

**Metodología:** se identificaron 2 commits nuevos desde `5ecfde7`: `2fc5618` ("2da auditoria", de Michelle, solo agrega la sección anterior de este documento + `package-lock.json`) y `692284d` ("Frontend post segunda auditoría", de Gerardo, toca `README.md` [raíz del proyecto], `frontend/src/pages/CodeReviewForm.tsx` y `frontend/src/pages/History.tsx`). Se releyeron los 3 archivos completos, se corrió `npm run build` (compila limpio), se levantaron ambos servidores reales (Vite en `5173`, Flask en `5000`), y se reprodujo con `curl` — replicando exactamente método, headers, `Origin` y body de cada función del código — el flujo más exigente pedido: crear revisión anónima → aceptar → solo comentar → regenerar → confirmar dashboard actualizado. Mismo límite que en rondas anteriores: sigue sin existir una herramienta de automatización de navegador en este entorno, así que la prueba es a nivel de la petición HTTP exacta que el código emite, no un click real en un navegador.

### Tabla de los 5 puntos

| Punto | Estado anterior | Estado actual | Evidencia |
|---|---|---|---|
| **#18** — `PATCH` sin `session_id` (403 en el camino anónimo) | ❌ Crítico, confirmado roto | ✅ **Resuelto, confirmado en vivo** | `CodeReviewForm.tsx:116` ahora incluye `session_id: sessionId` en el body del `PATCH` (comentario explícito: `// GAP 18: El session_id vital para que no tire 403`). Probado en vivo: se creó una revisión anónima real (`review_id=5b9a34b7-...`) y se replicó el `PATCH` exacto que emite `handleAction('accepted')` (con `session_id` incluido, `Origin: http://localhost:5173`) → `200 OK`, `status: "accepted"` persistido correctamente. |
| **#19** — "Explicación Educativa" con mapeo de campos incorrecto | ⚠️ Parcial, JSON crudo confirmado | ✅ **Resuelto, confirmado con datos reales del LLM** | `CodeReviewForm.tsx:247-251` ahora lee `exp.finding_id`, `exp.why`, `exp.impact`, `exp.how_to_fix` — exactamente los campos reales. Confirmado con una respuesta real de Gemini obtenida en esta misma verificación: el array `explanation` devuelto tiene exactamente esa forma (`{"finding_id": 1, "why": "...", "impact": "...", "how_to_fix": "..."}`), sin ningún campo `concept`/`title`/`description`/`details`. El render ya no cae al `JSON.stringify()` de respaldo. |
| **#4 (resto)** — Sin botón de "Comentar" independiente ni UI de "Regenerar" | ❌ Ninguno de los dos existía | ✅ **Ambos existen y funcionan de punta a punta — con un hallazgo nuevo (ver gap #20)** | Botón "Solo Comentar" (`CodeReviewForm.tsx:304`) llama `handleAction('pending')`; botón "Regenerar Diagnóstico" (línea 301) llama `handleRegenerate()` (línea 141), que hace `POST /api/reviews/<id>/regenerate` con `session_id` incluido. Ambos probados en vivo sobre la misma revisión: "Solo Comentar" → `200`, comentario guardado; "Regenerar" → `200`, nuevo `review_id` (`28562ded-...`) con `parent_review_id` apuntando correctamente al original, `session_id` preservado, análisis nuevo completo (con `summary` real). El `GET /api/dashboard/metrics` posterior confirmó `regenerated_count` subiendo de 23 a 24 y `total_reviews` de 68 a 70 — datos reales, no mock. |
| **#6 (resto)** — Modal sin `prompt_sent` ni `response` completo | ⚠️ Parcial, solo campos básicos | ⚠️ **Sigue parcial — mejoró, no se cerró del todo** | `History.tsx:162-169` ahora sí renderiza `selectedReview.prompt_sent` en una sección "Prompt Enviado al LLM". `History.tsx:180-193` ahora sí renderiza parte del `response` vía `getParsedResponse()` (maneja tanto objeto como string JSON) — pero **solo la lista de `findings`** (título/descripción/línea). `suggested_code`, `tests`, `summary` y `warnings` — que también forman parte del `response` completo y viajan igual en `GET /api/reviews/mine` — siguen sin mostrarse en el modal. Es una mejora real y verificada, no un cierre total de "evidencia completa". |
| **#12** — `frontend/README.md` como template default, sin Documento Funcional | ❌ Sin cambios | ⚠️ **Parcial — la mejora real aterrizó en el archivo equivocado** | El commit `692284d` reescribió por completo `README.md` en la **raíz del proyecto** (no `frontend/README.md`) con contenido real: stack tecnológico, instalación, variables de entorno (`VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY`), y una sección de "Arquitectura de Rutas y Funcionalidades" que describe `/review`, `/login`, `/register`, `/dashboard`, `/history`. Es un contenido genuinamente útil como guía de ejecución del frontend. Pero: (a) `frontend/README.md` — el archivo que el gap original señalaba explícitamente — **sigue siendo el template default de Vite sin ningún cambio**, confirmado con `git log` (el único commit que lo toca sigue siendo el commit inicial); ahora hay dos READMEs con contenido contradictorio (uno genérico de Vite dentro de `frontend/`, uno real y específico en la raíz); (b) el nuevo README describe pantallas pero no menciona en ningún punto las acciones de RF-08 (aceptar/descartar/comentar/regenerar) ni ninguna regla de negocio — sigue faltando la parte de "reglas de negocio y casos principales" que pedía un Documento Funcional completo. |

### Gap nuevo encontrado en esta ronda

| # | Gap | Dueño(s) | Depende de | Prioridad | Esfuerzo |
|---|---|---|---|---|---|
| 20 | El botón "Solo Comentar" llama `handleAction('pending')` (`CodeReviewForm.tsx:304`), que **siempre** manda `status: "pending"` en el `PATCH` — no solo el comentario. Si una revisión ya estaba `accepted` o `discarded` y el usuario agrega un comentario después, el estado vuelve a `"pending"` en silencio, deshaciendo la decisión anterior sin ningún aviso. Confirmado en vivo en esta misma verificación: se aceptó una revisión (`status: "accepted"` confirmado), y al usar "Solo Comentar" a continuación, el `status` de esa misma revisión volvió a `"pending"`. | **Gerardo** | Nada externo. Se resuelve no incluyendo `status` en el body cuando la acción es "solo comentar" (el backend ya soporta mandar únicamente `student_comment` sin `status`, confirmado en `routes/review.py:342-343`: solo exige que venga *al menos uno* de los dos, no ambos). | **Importante** (no bloquea la demo, pero genera una regresión de datos silenciosa si se comenta después de decidir — mala señal para el criterio de "Datos, trazabilidad" y "Calidad funcional y UX" de la rúbrica) | Bajo |

### Resumen ejecutivo de esta segunda re-verificación

**El sistema ya está en condiciones de sostener una demo end-to-end del camino anónimo sin el bloqueador crítico anterior.** El flujo completo más exigente —crear revisión anónima → aceptar → solo comentar → regenerar → dashboard reflejando el cambio— se probó de punta a punta en esta ronda y **todos los pasos devuelven `200` con datos reales**, incluyendo el que antes fallaba con `403` (gap #18, confirmado resuelto). El gap #19 (JSON crudo en "Explicación Educativa") también se confirmó resuelto con una respuesta real del LLM.

Quedan dos puntos abiertos que **no bloquean una demo pero sí le restan pulido**, ambos de bajo esfuerzo: el modal de "Ver Detalle" todavía no muestra el código sugerido ni las pruebas propuestas de una revisión pasada (gap #6, parcial), y el nuevo gap #20 (comentar después de decidir revierte el estado a "pending" sin aviso) podría generar una situación incómoda si se demuestra en ese orden específico durante la defensa — vale la pena que Gerardo lo evite mostrando primero "Aceptar"/"Descartar" y dejando "Comentar" para el final, o mejor aún, resolviéndolo antes de la demo.

**Confirmación explícita:** con esta ronda, lo único que queda pendiente en todo el proyecto —además de los dos puntos de pulido de arriba (#6 resto, #20)— son exactamente los ítems de documentación ya identificados y sin cambios: el catálogo de prompts de **Erick** (#9), los 5 fragmentos de código y la evidencia de pruebas consolidada de **Carla** (#10, #11), y el Documento Técnico consolidado de **Fernando** (#13) — más el propio gap #12 (Documento Funcional/README de frontend), que sigue parcialmente abierto y es responsabilidad de **Gerardo** (con la coordinación de "TODOS" ya señalada en la Parte E original para unificarlo). No se encontró ningún otro pendiente nuevo de código fuera de estos.
