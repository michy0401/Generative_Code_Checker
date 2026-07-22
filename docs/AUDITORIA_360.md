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
