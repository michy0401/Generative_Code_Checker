# Backend - Sistema Inteligente de Revision de Codigo para Estudiantes

> Ver tambien: [README del proyecto](../README.md) (vision general del sistema completo) y
> [README del frontend](../frontend/README.md).

Backend en Flask que expone el modulo de IA de revision de codigo (`services/llm_connector.py`),
implementado siguiendo el pipeline documentado en la arquitectura del proyecto:
Input Processor -> Prompt Builder -> LLM Service -> Output Parser -> Response Validator.

Cada revision se persiste en Supabase (tabla `reviews`) a traves de `repositories/review_repository.py`.

Para el detalle completo de cada endpoint (campos, respuestas de ejemplo, todos los codigos de
error), ver **[`docs/REFERENCIA_API.md`](docs/REFERENCIA_API.md)** - es la fuente de verdad para
quien integre el frontend contra esta API. Este README cubre instalacion y ejecucion, no el
contrato de la API en si.

## Requisitos

- Python 3.10+
- Una API key de Google AI Studio (Gemini)
- Un proyecto de Supabase con las migraciones de `migrations/` ya ejecutadas (en orden)

## Instalacion

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

## Base de datos (Supabase)

Correr manualmente, en orden, el contenido de cada archivo en `migrations/` en el SQL Editor de
Supabase antes de usar la persistencia. El backend no ejecuta migraciones por si solo.

- `001_init_supabase.sql`: crea `public.students`, `public.reviews`, el trigger que sincroniza
  `auth.users -> public.students`, y los indices.
- `002_add_parent_review.sql`: agrega `reviews.parent_review_id` (relacion entre una revision y
  la revision anterior que la origino, usada por `POST /api/reviews/<id>/regenerate`).
- `003_add_status_comment_prompt.sql`: agrega `reviews.status` (`pending`/`accepted`/`discarded`,
  revision humana - RF-08, `PATCH /api/reviews/<id>`), `reviews.student_comment` (comentario libre
  opcional), y `reviews.prompt_sent` (el prompt final que efectivamente se mando al LLM - RF-09,
  trazabilidad).

## Variables de entorno

Copia `.env.example` a `.env` y completa los valores:

| Variable | Descripcion |
|---|---|
| `GOOGLE_API_KEY` | API key de Google AI Studio (Gemini). Requerida para llamadas reales al LLM. |
| `FLASK_ENV` | `development` o `production`. |
| `DEBUG` | `True`/`False`. Habilita el modo debug de Flask. |
| `SUPABASE_URL` | URL del proyecto de Supabase. Tambien se usa para construir la URL del JWKS al validar JWT (ver `docs/AUTH_PARA_FRONTEND.md`). |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key de Supabase (acceso con privilegios, solo backend). |
| `ALLOWED_ORIGINS` | Lista de origenes permitidos para CORS, separados por coma (ej. `http://localhost:3000,http://127.0.0.1:3000`). Nunca se usa `"*"`: el sistema maneja JWT. |
| `MAX_REQUEST_SIZE_BYTES` | Tamano maximo (bytes) del body de un request. Default `102400` (100 KB). Si se supera, Flask responde `413` en JSON. |
| `MAX_STUDENT_CODE_CHARS` | Cantidad maxima de caracteres de `student_code`. Default `20000`. Si se supera, el Input Processor corta con `400` antes de llamar al LLM (no gasta cuota de Gemini). |
| `REVIEW_RATE_LIMIT` | Limite de requests por IP a `POST /api/review` y `POST /api/reviews/<id>/regenerate` (los dos endpoints que consumen cuota del LLM), formato de `flask-limiter` (ej. `30 per minute`). Default `30 per minute`. Al superarse, responde `429` en JSON con un mensaje que aclara que es un limite propio del backend, no la cuota de Gemini. |

`GOOGLE_API_KEY` solo es necesaria para `tests/test_llm_connection.py`, `tests/check_models.py`
y para el endpoint `POST /api/review` en uso real. `tests/test_mock_connection.py` no la necesita.

Si `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` faltan o Supabase no responde, `POST /api/review`
sigue devolviendo el analisis igual (el usuario no pierde su resultado), pero la revision no
queda guardada y el fallo se loguea en la terminal del servidor.

## Correr el servidor

```bash
python app.py
# o
flask --app app run
```

## Documentacion interactiva de la API (Swagger)

Con el servidor corriendo, **`GET /api/docs`** tiene la referencia completa y actualizada de
los 10 endpoints (`/health`, `/api/review`, `/api/reviews/<id>` [GET y PATCH], `/api/reviews`,
`/api/reviews/mine`, `/api/reviews/<id>/regenerate`, `/api/reviews/<id>/history`,
`/api/dashboard/metrics`, `/api/dashboard/mine`): metodo, parametros, si requiere autenticacion (y de que tipo),
estructura de respuesta y todos los codigos de status posibles. Se puede probar cada endpoint
directamente desde el navegador, incluyendo pegar un JWT en el boton "Authorize" para los que lo
requieren o aceptan.

`review_type` (en `POST /api/review` y opcionalmente en `/regenerate`) solo acepta una lista
controlada de valores (RF-03): Errores, Buenas practicas, Legibilidad, Estructura, Seguridad
basica, Rendimiento, Pruebas sugeridas (no distingue mayusculas/tildes). Un valor fuera de esa
lista responde `400` con los valores permitidos en el mensaje.

`PATCH /api/reviews/<id>` permite revision humana (RF-08): aceptar/descartar (`status`) y/o dejar
un comentario libre (`student_comment`) sobre una revision propia, con el mismo ownership check
que el resto de los endpoints de revision puntual.

`GET /api/dashboard/metrics` (RF-10) devuelve metricas agregadas de TODO el sistema (no de un
estudiante particular) para que el frontend arme el tablero: total de revisiones, conteo por
lenguaje, conteo por status, cantidad de regeneraciones, y el top 10 de findings mas frecuentes.
Publico, no requiere autenticacion. Este backend solo expone los datos - la visualizacion es
responsabilidad del frontend.

El JSON crudo de la spec (OpenAPI/Swagger 2.0) esta en `GET /api/openapi.json`, para importar en
Postman o generadores de clientes.

Este README y `docs/AUTH_PARA_FRONTEND.md` explican el panorama general y el flujo de
autenticacion; para el detalle tecnico de cada endpoint (parametros exactos, respuestas, codigos
de error), tanto `docs/REFERENCIA_API.md` (para leer) como `/api/docs` (para probar en vivo con
"Try it out") son la fuente de verdad - deberian decir siempre lo mismo.

`POST /api/review` acepta opcionalmente el header `Authorization: Bearer <token>`: si el
token es valido, la revision queda asociada al `student_id` del usuario; si no se manda ningun
token, sigue funcionando en modo anonimo con `session_id` (comportamiento identico al anterior).
El backend nunca implementa signup/login - eso es responsabilidad del frontend con `supabase-js`
(ver `docs/AUTH_PARA_FRONTEND.md`).

## Correr los tests

Hay dos capas de tests, con propositos distintos:

- **`pytest` (`tests/unit/`)** — tests unitarios rapidos (corren en un par de segundos) de la
  logica que no depende de red: Input Processor, Response Validator, ownership check, el
  reintento con Few-Shot Examples, reintentos ante fallas transitorias, fallo de persistencia
  con LLM exitoso, y la agregacion de metricas del dashboard. Todo lo externo (Gemini, Supabase)
  esta mockeado - **no necesitan el servidor
  levantado, ni Supabase real, ni gastar cuota de Gemini, ni ninguna variable de entorno real
  configurada**. Es lo que conviene correr seguido mientras se desarrolla, o en CI.
- **`tests/test_api_manual.py`** — test de integracion end-to-end: 30 casos contra el servidor y
  el proyecto de Supabase **reales** (algunos gastan cuota real de Gemini). Sigue siendo la unica
  forma de probar el flujo completo tal como lo veria un cliente real (JWT real via Supabase Auth,
  persistencia real, rate limiting real, etc.). No lo reemplaza `pytest` ni viceversa.

```bash
# Tests unitarios (rapidos, sin red, sin credenciales) - correr desde backend/
pytest

# No requiere internet ni API key
python tests/test_mock_connection.py

# Requiere GOOGLE_API_KEY valida en .env y conexion a internet
python tests/test_llm_connection.py

# Lista los modelos disponibles para la API key configurada
python tests/check_models.py

# Con el servidor corriendo (python app.py) en otra terminal: 30 casos end-to-end
python tests/test_api_manual.py
```

## Estructura

```
backend/
├── app.py                        # Application factory de Flask (CORS + Swagger se configuran aca)
├── config.py                      # Configuracion por entorno (.env)
├── extensions.py                  # Limiter de flask-limiter (compartido entre app.py y routes/)
├── logging_config.py              # Configuracion centralizada de logging
├── requirements.txt
├── pytest.ini                     # Config minima para que "pytest" encuentre tests/unit/
├── migrations/
│   ├── 001_init_supabase.sql      # Se corre a mano en el SQL Editor de Supabase
│   ├── 002_add_parent_review.sql # idem - agrega reviews.parent_review_id
│   └── 003_add_status_comment_prompt.sql # idem - status/student_comment/prompt_sent
├── docs/
│   ├── REFERENCIA_API.md          # Referencia completa de los 10 endpoints (fuente de verdad)
│   ├── AUTH_PARA_FRONTEND.md      # Como el frontend debe mandar el JWT de Supabase Auth
│   └── PROMPT_CHANGELOG.md        # Historial de versiones del SYSTEM_PROMPT
├── services/
│   ├── llm_connector.py           # Modulo de IA
│   ├── supabase_client.py         # Cliente unico de Supabase (perezoso)
│   └── review_ownership.py        # Ownership check para regenerar/ver historial
├── repositories/
│   └── review_repository.py       # Unico punto de acceso a la tabla `reviews`
├── middleware/
│   └── auth.py                    # Validacion local de JWT (Supabase Auth)
├── schemas/
│   └── response_schema.json       # Response Schema v1.0
├── routes/
│   ├── review.py                  # Blueprint de /api/review y /api/reviews
│   └── dashboard.py                # Blueprint de /api/dashboard/metrics (RF-10)
└── tests/
    ├── test_mock_connection.py
    ├── test_llm_connection.py
    ├── test_api_manual.py         # Integracion end-to-end (servidor + Supabase reales)
    ├── check_models.py
    └── unit/                      # Tests unitarios de pytest (sin red, sin credenciales)
        ├── test_input_processor.py
        ├── test_response_validator.py
        ├── test_review_ownership.py
        ├── test_few_shot_trigger.py
        ├── test_llm_retries.py
        ├── test_persistence_failure.py
        ├── test_dashboard_metrics.py
        └── test_expired_token.py  # Documenta por que este caso no se automatiza
```
