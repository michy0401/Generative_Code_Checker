# Backend - Sistema Inteligente de Revision de Codigo para Estudiantes

Backend en Flask que expone el modulo de IA de revision de codigo (`services/llm_connector.py`),
implementado siguiendo el pipeline documentado en la arquitectura del proyecto:
Input Processor -> Prompt Builder -> LLM Service -> Output Parser -> Response Validator.

Cada revision se persiste en Supabase (tabla `reviews`) a traves de `repositories/review_repository.py`.

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
los 7 endpoints (`/health`, `/api/review`, `/api/reviews/<id>`, `/api/reviews`, `/api/reviews/mine`,
`/api/reviews/<id>/regenerate`, `/api/reviews/<id>/history`): metodo, parametros, si requiere
autenticacion (y de que tipo), estructura de respuesta y todos los codigos de status posibles.
Se puede probar cada endpoint directamente desde el navegador, incluyendo pegar un JWT en el
boton "Authorize" para los que lo requieren o aceptan.

El JSON crudo de la spec (OpenAPI/Swagger 2.0) esta en `GET /api/openapi.json`, para importar en
Postman o generadores de clientes.

Este README y `docs/AUTH_PARA_FRONTEND.md` explican el panorama general y el flujo de
autenticacion; para el detalle tecnico de cada endpoint (parametros exactos, respuestas, codigos
de error), `/api/docs` es la fuente de verdad.

`POST /api/review` acepta opcionalmente el header `Authorization: Bearer <token>`: si el
token es valido, la revision queda asociada al `student_id` del usuario; si no se manda ningun
token, sigue funcionando en modo anonimo con `session_id` (comportamiento identico al anterior).
El backend nunca implementa signup/login - eso es responsabilidad del frontend con `supabase-js`
(ver `docs/AUTH_PARA_FRONTEND.md`).

## Correr los tests

```bash
# No requiere internet ni API key
python tests/test_mock_connection.py

# Requiere GOOGLE_API_KEY valida en .env y conexion a internet
python tests/test_llm_connection.py

# Lista los modelos disponibles para la API key configurada
python tests/check_models.py

# Con el servidor corriendo (python app.py) en otra terminal: 16 casos end-to-end
python tests/test_api_manual.py
```

## Estructura

```
backend/
├── app.py                        # Application factory de Flask (CORS + Swagger se configuran aca)
├── config.py                      # Configuracion por entorno (.env)
├── logging_config.py              # Configuracion centralizada de logging
├── requirements.txt
├── migrations/
│   ├── 001_init_supabase.sql      # Se corre a mano en el SQL Editor de Supabase
│   └── 002_add_parent_review.sql # idem - agrega reviews.parent_review_id
├── docs/
│   └── AUTH_PARA_FRONTEND.md      # Como el frontend debe mandar el JWT de Supabase Auth
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
│   └── review.py                  # Blueprint de /api/review y /api/reviews
└── tests/
    ├── test_mock_connection.py
    ├── test_llm_connection.py
    ├── test_api_manual.py
    └── check_models.py
```
