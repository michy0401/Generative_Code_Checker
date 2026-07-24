# Sistema Inteligente de Revisión de Código para Estudiantes

Proyecto final de la materia *Introducción a la Programación con IA* (Ciclo II - 2026, Ingeniería
de Software y Negocios Digitales, ESEN). El sistema usa IA generativa (Google Gemini) como
componente central del flujo: el estudiante envía un fragmento de código junto con el contexto del
ejercicio, la IA genera un diagnóstico educativo estructurado (errores, mejoras, recomendaciones,
explicación de cada hallazgo, código sugerido y pruebas propuestas), y el estudiante decide qué
hacer con esa revisión — aceptarla, descartarla, comentarla o pedir una nueva pasada de análisis.

No es un simple envoltorio de un chat de IA: el sistema registra cada revisión con su prompt real,
valida la respuesta del modelo contra un formato fijo, y mantiene trazabilidad completa de las
decisiones humanas sobre cada diagnóstico.

## Estructura del proyecto

```
Generative_Code_Checker/
├── backend/              # API en Flask + integración con Gemini + persistencia en Supabase
├── frontend/              # Interfaz en React + Vite que consume esa API

```

## Stack tecnológico

| Parte | Tecnología |
|---|---|
| Backend | Python 3.10+, Flask, `google-genai` (Gemini), Supabase (Postgres) |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Autenticación | Supabase Auth (JWT asimétrico, ES256), compartida entre backend y frontend |
| Base de datos | Supabase Postgres (tabla `reviews`, ver esquema en `backend/docs/REFERENCIA_API.md`) |

## Flujo end-to-end

1. El estudiante (autenticado o anónimo) ingresa código y el contexto del ejercicio en el frontend (`/review`).
2. El frontend manda ese input al backend (`POST /api/review`).
3. El backend arma un prompt estructurado con guardrails educativos y se lo envía a Gemini.
4. La respuesta se valida contra un Response Schema fijo (6 secciones) y se persiste en Supabase junto con el prompt real que se usó.
5. El frontend muestra el diagnóstico completo: hallazgos, explicación, código sugerido y pruebas.
6. El estudiante decide: aceptar, descartar, comentar o regenerar — cualquiera de esas acciones vuelve a pasar por el backend (`PATCH`/`POST .../regenerate`).
7. El dashboard (`/dashboard`) y el historial (`/history`) consumen esas mismas revisiones persistidas para mostrar métricas agregadas y trazabilidad individual.

## Cómo levantar el proyecto

Este README no repite pasos de instalación — cada parte tiene el suyo, con sus propias variables
de entorno y comandos:

- **Backend**: ver [`backend/README.md`](backend/README.md) — venv, `.env`, migraciones de Supabase, cómo correr el servidor y los tests.
- **Frontend**: ver [`frontend/README.md`](frontend/README.md) — instalación, `.env`, rutas de la aplicación y reglas de negocio del control humano (RF-08).

Ambos servidores tienen que correr en paralelo (backend en `http://127.0.0.1:5000`, frontend en
`http://localhost:5173`) para que el flujo completo funcione — el frontend llama directamente al
backend por HTTP, no hay proxy ni servidor intermedio.

## Documentación de la API

- Referencia completa de los 10 endpoints (campos, respuestas de ejemplo, todos los códigos de error): [`backend/docs/REFERENCIA_API.md`](backend/docs/REFERENCIA_API.md)
- Documentación interactiva (Swagger UI, "Try it out" en vivo contra el servidor real): `http://127.0.0.1:5000/api/docs/`, con el backend corriendo
- Detalle del flujo de autenticación (JWT de Supabase Auth, JWKS/ES256): [`backend/docs/AUTH_PARA_FRONTEND.md`](backend/docs/AUTH_PARA_FRONTEND.md)
- Historial de versiones del prompt del sistema: [`backend/docs/PROMPT_CHANGELOG.md`](backend/docs/PROMPT_CHANGELOG.md)

## Documentación adicional

- `rubrica_evaluacion/`: enunciado oficial del proyecto y rúbrica de evaluación de la materia (no se modifica).
- `docs/`: auditorías del sistema completo (backend + frontend integrados) realizadas durante el desarrollo.
