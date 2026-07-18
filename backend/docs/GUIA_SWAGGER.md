# Guía de Swagger UI (verificada de punta a punta)

Esta guía fue escrita reproduciendo el flujo completo contra el servidor real (arranque desde
cero, `curl` simulando exactamente lo que "Try it out" dispara, un usuario real de Supabase Auth
para el JWT). Cada respuesta de ejemplo de este documento es una respuesta real capturada durante
esa verificación, no una respuesta inventada.

**Limitación de esta verificación:** se hizo a nivel HTTP (arranque del servidor, cada ruta, cada
request que "Try it out" dispara). No se abrió un navegador real con DevTools, así que no se pudo
confirmar visualmente el renderizado ni la consola de JavaScript. Si después de seguir esta guía
algo se ve raro en el navegador (una pantalla en blanco, un error de JS), no es algo que esta
verificación haya podido descartar — reportalo aparte.

## Diagnóstico: ¿había algo roto?

**No, a nivel backend no había ningún endpoint roto, ninguna ruta mal configurada, ni ningún
asset estático faltante.** Todo lo que se pudo verificar por HTTP funciona correctamente (detalle
completo en la sección de Troubleshooting). Lo que sí se encontró y se corrigió fue un punto de
confusión real y confirmado: el campo "Authorize" de Swagger UI **no agrega automáticamente el
prefijo `Bearer`** al token — hay que escribirlo a mano. Si se pega solo el token:

- En un endpoint de autenticación **obligatoria** (`GET /api/reviews/mine`): da `401` claro.
- En un endpoint de autenticación **opcional** (`POST /api/review`, `/regenerate`): responde
  `200` igual, pero **en modo anónimo**, sin ningún aviso — el request "funciona" pero la revisión
  no queda asociada al usuario. Esto se confirmó reproduciéndolo con un usuario real.

Se corrigió mejorando la descripción del campo `Bearer` en `app.py` (`SWAGGER_TEMPLATE`) para que
esa advertencia aparezca directamente en el modal de "Authorize" de Swagger UI, en vez de quedar
solo en esta guía. No se cambió ningún comportamiento de la API (el diseño de "auth opcional
degrada a anónimo en silencio" es intencional, no un bug) — se corrigió únicamente la
documentación que lo explica.

---

## 1. Levantar el servidor

Desde `backend/`, con el `.env` real ya configurado:

```bash
python app.py
```

Consola exacta que confirma que arrancó bien (verificada en esta sesión):

```
 * Serving Flask app 'app'
 * Debug mode: on
2026-07-17 17:21:19 [INFO] werkzeug: WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
2026-07-17 17:21:19 [INFO] werkzeug: Press CTRL+C to quit
```

También puede aparecer, antes de esas líneas, un `UserWarning` de `flask-limiter` sobre
almacenamiento en memoria para el rate limit — es esperado (no hay Redis configurado) y no impide
que el servidor funcione.

**El puerto es siempre `5000`** (Flask no toma ningún puerto de `.env`; `app.run()` no especifica
uno, así que usa el default). Si algo más ya está usando el puerto 5000, el arranque falla con un
error de "Address already in use" en vez de las líneas de arriba — si ves eso, cerrá el otro
proceso primero.

## 2. Abrir Swagger UI

**URL exacta: `http://127.0.0.1:5000/api/docs/`** (con la barra final).

Esto no es arbitrario: `flasgger` está configurado en `app.py` con `"specs_route": "/api/docs/"`
(barra incluida). Si entrás a `http://127.0.0.1:5000/api/docs` (**sin** la barra), Flask responde
un **308 Permanent Redirect** hacia la URL con barra — confirmado con esta sesión corriendo:

```
HTTP/1.1 308 PERMANENT REDIRECT
Location: http://127.0.0.1:5000/api/docs/
```

Cualquier navegador sigue ese redirect automáticamente, así que en la práctica **las dos URLs
funcionan** — no hace falta acordarse de la barra. Si estás probando con una herramienta que NO
sigue redirects automáticamente (algunos clientes HTTP con esa opción desactivada), vas a ver el
308 en vez del HTML y puede parecer "no carga" — ese es el motivo.

Al cargar, Swagger UI pide su JSON de especificación desde `GET /api/openapi.json` (confirmado
leyendo el HTML servido: `url: "/api/openapi.json"`) y sus assets estáticos desde
`/flasgger_static/...` (CSS, `swagger-ui-bundle.js`, `swagger-ui-standalone-preset.js`,
`lib/jquery.min.js`). Los 4 se verificaron con `200` en esta sesión.

## 3. Generar un `session_id` de prueba

Para probar cualquier endpoint que dependa de una revisión anónima (`GET /api/reviews`,
`GET /api/reviews/<id>`, `PATCH`, `/regenerate`, `/history`):

1. En Swagger UI, abrí `POST /api/review`, "Try it out", completá el body de ejemplo y ejecutá.
2. En la respuesta, copiá el valor de `"session_id"` (y de paso `"review_id"`, lo vas a necesitar
   para los pasos siguientes).

No hace falta mandar `session_id` en el request — si no lo mandás, el backend genera uno nuevo y
te lo devuelve.

## 4. Obtener un JWT de prueba

El proyecto de Supabase usa **llaves asimétricas (ECC P-256, algoritmo ES256)** validadas contra
el JWKS real del proyecto — no hay ningún secreto compartido con el que se pueda "fabricar" un
token válido a mano. Se verificó en esta sesión que esto sigue siendo así (`middleware/auth.py`
no cambió) y que el flujo de abajo sigue funcionando: crear un usuario real vía la Auth Admin API
(con la `service_role` key) y loguearlo para obtener un `access_token` real firmado por Supabase.
Es exactamente lo que ya hacen los casos 12/16 de `tests/test_api_manual.py`.

Con el entorno virtual activado, desde `backend/`:

```python
import os, uuid
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL").strip()
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY").strip()

# Dos clientes separados a propósito: sign_in_with_password() muta el estado
# interno del cliente con el que se llama (dejaría de mandar la service_role key).
admin_client = create_client(url, key)
auth_client = create_client(url, key)

email = f"prueba-{uuid.uuid4()}@example.com"
password = f"Test-{uuid.uuid4()}!"
created = admin_client.auth.admin.create_user({"email": email, "password": password, "email_confirm": True})
session = auth_client.auth.sign_in_with_password({"email": email, "password": password})

print("access_token:", session.session.access_token)
print("user_id (para borrar despues):", created.user.id)
```

Guardá el `access_token` que imprime — es el JWT que vas a pegar en "Authorize".

Para limpiar el usuario de prueba después (opcional, pero recomendado para no acumular usuarios
de prueba en el proyecto):

```python
admin_client.table("reviews").delete().eq("student_id", created.user.id).execute()
admin_client.auth.admin.delete_user(created.user.id)
```

## 5. Usar el botón "Authorize"

1. Arriba a la derecha de Swagger UI, click en **Authorize**.
2. En el campo `Bearer` (tipo `apiKey`, header `Authorization`), escribí **literalmente la
   palabra `Bearer`, un espacio, y después el token**:

   ```
   Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6...
   ```

3. Click en "Authorize" y después "Close".

**Confirmado con un usuario real en esta sesión** (`GET /api/reviews/mine`):

| Header enviado | Resultado |
|---|---|
| `Authorization: Bearer <token>` | `200`, lista real de revisiones del usuario |
| `Authorization: <token>` (sin `Bearer `) | `401 {"error": "Se requiere autenticacion."}` en endpoints obligatorios |
| `Authorization: <token>` (sin `Bearer `) en `POST /api/review` (auth opcional) | **`200`, pero en modo anónimo** - la revisión no queda asociada al usuario, sin ningún error |

Swagger UI **no agrega el prefijo `Bearer` automáticamente** para este tipo de seguridad
(`apiKey`) - a diferencia de otras herramientas/esquemas (`http`, `bearer` de OpenAPI 3), acá hay
que escribirlo vos. Esto ya quedó reforzado en la descripción del campo dentro del propio Swagger
UI (ver `app.py`).

## 6. Ejemplo completo end-to-end

Flujo real, en orden, con las respuestas reales obtenidas en esta verificación (recortadas donde
son muy largas).

### 6.1 Crear una revisión — `POST /api/review`

Body:
```json
{
  "language": "Python",
  "exercise": "Diagnostico Swagger",
  "level": "Basico",
  "review_type": "Buenas practicas",
  "student_code": "def suma(a, b): return a + b"
}
```

Respuesta (`200`, recortada):
```json
{
  "review_id": "5282ed5d-7be9-4fab-8543-05c11e93608f",
  "session_id": "2890276b-ae07-4ac1-aa30-0780f45f151f",
  "summary": {
    "language": "Python",
    "review_type": "Buenas practicas",
    "overall_assessment": "El código es funcionalmente correcto...",
    "score": 65
  },
  "findings": ["... 3 findings sobre type hints, docstring y formato PEP 8 ..."],
  "explanation": ["..."],
  "suggested_code": { "improved_code": "def suma(a: int, b: int) -> int:\n    ...", "changes_summary": ["..."] },
  "tests": ["..."],
  "warnings": ["..."]
}
```

Guardá `review_id` y `session_id` de la respuesta para los pasos siguientes.

### 6.2 Consultarla — `GET /api/reviews/{review_id}?session_id=...`

Devuelve la fila completa (`200`), incluyendo `status: "pending"` (default de toda revisión
nueva) y `prompt_sent` (el prompt real que se mandó al LLM).

### 6.3 Aceptarla — `PATCH /api/reviews/{review_id}`

Body:
```json
{ "status": "accepted", "session_id": "2890276b-ae07-4ac1-aa30-0780f45f151f" }
```

Respuesta (`200`): la fila actualizada, con `"status": "accepted"`.

### 6.4 Regenerarla — `POST /api/reviews/{review_id}/regenerate`

Body:
```json
{ "session_id": "2890276b-ae07-4ac1-aa30-0780f45f151f", "motivo_regeneracion": "Quiero otra opinion" }
```

Respuesta (`200`, real): nueva revisión con `review_id: "8f991fbb-c905-4079-b8b0-ad15f3a6c520"`,
`parent_review_id` apuntando a la original, `score` distinto al de la primera pasada (45 en esta
corrida) - la regeneración es una fila nueva, nunca sobreescribe la original.

### 6.5 Ver el historial — `GET /api/reviews/{review_id}/history?session_id=...`

Respuesta (`200`, real): las 2 revisiones de la cadena (la original `accepted` + la regeneración
`pending`), ordenadas por fecha de creación - podés consultar con el `review_id` de cualquiera de
las dos y da la misma cadena completa.

### 6.6 Ver el dashboard — `GET /api/dashboard/metrics`

No requiere autenticación ni ningún parámetro. Respuesta real (`200`) de esta sesión de
verificación (los números reflejan todo lo acumulado en el proyecto de Supabase, no solo esta
corrida):
```json
{
  "total_reviews": 60,
  "reviews_by_language": { "Python": 60 },
  "reviews_by_status": { "accepted": 4, "pending": 56 },
  "regenerated_count": 20,
  "most_frequent_findings": [
    { "title": "Falta de anotaciones de tipo (Type Hinting)", "count": 34 },
    { "title": "Falta de documentacion (Docstring)", "count": 27 },
    { "title": "Error de sintaxis en la definicion de la funcion", "count": 14 }
  ]
}
```

---

## Troubleshooting

Problemas reales considerados y descartados/explicados durante esta verificación (arranque
limpio del servidor, sin dar nada por sentado):

| Síntoma | ¿Es un problema real? | Explicación |
|---|---|---|
| `http://127.0.0.1:5000/api/docs` (sin barra) da un redirect en vez de HTML directo | No | Es un `308` estándar de Flask hacia `/api/docs/`. Un navegador lo sigue solo. Si tu cliente HTTP no sigue redirects, vas a ver el 308 - no es que "no funcione". |
| El servidor no arranca en el puerto 5000 | Revisar aparte | El puerto es siempre 5000 (no viene de `.env`). Si otro proceso ya lo está usando, Flask falla con "Address already in use" - cerrá el otro proceso, no cambia nada en el código. |
| Pego el JWT y todo "funciona" pero las revisiones no aparecen en `GET /api/reviews/mine` | **Sí, es el problema real encontrado en esta tarea** | Te faltó escribir `Bearer ` antes del token en el campo Authorize. En endpoints de auth opcional esto NO da ningún error - el request responde 200 en modo anónimo. Fijate que el campo Authorize en Swagger UI ahora lo advierte explícitamente. |
| `GET /api/reviews/mine` da `401` | No es un bug | Es el comportamiento esperado si no autorizaste, o si autorizaste sin el prefijo `Bearer`. Volvé a autorizar con el formato `Bearer <token>` completo. |
| ¿`ALLOWED_ORIGINS` de CORS bloquea Swagger UI? | No, confirmado | Swagger UI se sirve y hace sus requests desde el mismo origen del backend (`http://127.0.0.1:5000`) - un request same-origin nunca pasa por la política de CORS del navegador, sin importar qué diga `ALLOWED_ORIGINS`. Se confirmó con requests reales que orígenes permitidos (`http://localhost:3000`) reciben el header `Access-Control-Allow-Origin` correcto y orígenes no permitidos (`http://evil.com`) no lo reciben - CORS funciona como se espera. |
| Nota menor de CORS (no bloquea nada) | Detalle a saber, no un problema | `flask-cors` con la config actual manda `Access-Control-Allow-Origin` incluso en requests que no traen ningún header `Origin` (comportamiento default `always_send` de la librería, no algo que este proyecto configuró explícitamente). Es inofensivo: el navegador solo consulta ese header en requests cross-origin reales, y ahí sigue funcionando correctamente (confirmado). No se tocó, porque no está roto y no es lo que se estaba diagnosticando. |
| Un `finding` o `review_type` con tildes se ve como `?` o con caracteres raros en la terminal de Windows | No es un bug del backend | Es un tema de encoding de la consola de Windows al imprimir UTF-8, no del JSON en sí (el JSON que viaja por HTTP es UTF-8 válido). En el navegador (Swagger UI) se ve bien. |
| Pantalla en blanco o error de JavaScript en el navegador | **No se pudo descartar en esta verificación** | Esta verificación se hizo a nivel HTTP (`curl`), no con un navegador real. Si esto pasa, es lo primero a revisar con DevTools abierto (pestaña Console y Network) - y a reportar, porque no fue parte de lo confirmado acá. |
