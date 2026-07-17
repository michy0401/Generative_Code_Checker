"""Entry point de la aplicacion Flask - application factory."""

import logging

# pyrefly: ignore [missing-import]
from flasgger import Swagger
# pyrefly: ignore [missing-import]
from flask import Flask, jsonify
# pyrefly: ignore [missing-import]
from flask_cors import CORS
# pyrefly: ignore [missing-import]
from werkzeug.exceptions import HTTPException

from config import get_config
from extensions import limiter
from logging_config import configure_logging
from routes.review import review_bp

logger = logging.getLogger(__name__)

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/api/openapi.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs/",
}

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "Sistema Inteligente de Revision de Codigo - API",
        "description": (
            "Backend de revision de codigo con IA (Input Processor -> Prompt Builder -> "
            "LLM Service -> Output Parser -> Response Validator), persistencia en Supabase "
            "y autenticacion opcional via JWT de Supabase Auth. El login en si vive en el "
            "frontend (supabase-js) - ver docs/AUTH_PARA_FRONTEND.md."
        ),
        "version": "1.0.0",
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": (
                "JWT de una sesion de Supabase Auth. Formato: 'Bearer <access_token>'. "
                "Requerido solo en los endpoints marcados como autenticacion obligatoria; "
                "opcional (cambia el comportamiento pero no bloquea) en los demas."
            ),
        }
    },
    "definitions": {
        "Summary": {
            "type": "object",
            "required": ["language", "review_type", "overall_assessment", "score"],
            "properties": {
                "language": {"type": "string"},
                "review_type": {"type": "string"},
                "overall_assessment": {"type": "string"},
                "score": {"type": "integer", "minimum": 0, "maximum": 100},
            },
        },
        "Finding": {
            "type": "object",
            "required": ["id", "category", "severity", "title", "description", "line"],
            "properties": {
                "id": {"type": "integer"},
                "category": {"type": "string", "enum": ["Error", "Improvement", "Recommendation"]},
                "severity": {"type": "string", "enum": ["High", "Medium", "Low"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "line": {"type": "integer", "minimum": 1},
            },
        },
        "Explanation": {
            "type": "object",
            "required": ["finding_id", "why", "impact", "how_to_fix"],
            "properties": {
                "finding_id": {"type": "integer"},
                "why": {"type": "string"},
                "impact": {"type": "string"},
                "how_to_fix": {"type": "string"},
            },
        },
        "SuggestedCode": {
            "type": "object",
            "required": ["improved_code", "changes_summary"],
            "properties": {
                "improved_code": {"type": "string"},
                "changes_summary": {"type": "array", "items": {"type": "string"}},
            },
        },
        "TestCase": {
            "type": "object",
            "required": ["title", "description", "expected_result"],
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "expected_result": {"type": "string"},
            },
        },
        "ReviewResponse": {
            "type": "object",
            "description": (
                "Cumple exactamente schemas/response_schema.json (Response Schema v1.0), "
                "mas los metadatos de persistencia agregados por el endpoint."
            ),
            "required": ["summary", "findings", "explanation", "suggested_code", "tests", "warnings"],
            "properties": {
                "review_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Id de la revision persistida en Supabase. Ausente/null si fallo la persistencia (el analisis se devuelve igual).",
                },
                "session_id": {
                    "type": "string",
                    "description": "Id de sesion anonima (generado automaticamente si no se envio uno).",
                },
                "parent_review_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Solo presente en la respuesta de /regenerate: apunta a la revision original.",
                },
                "summary": {"$ref": "#/definitions/Summary"},
                "findings": {"type": "array", "items": {"$ref": "#/definitions/Finding"}},
                "explanation": {"type": "array", "items": {"$ref": "#/definitions/Explanation"}},
                "suggested_code": {"$ref": "#/definitions/SuggestedCode"},
                "tests": {"type": "array", "items": {"$ref": "#/definitions/TestCase"}},
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
        },
        "ReviewRow": {
            "type": "object",
            "description": "Fila cruda de la tabla `reviews`, tal como la devuelven los endpoints GET.",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "student_id": {"type": "string", "format": "uuid", "description": "null si es una revision anonima."},
                "session_id": {"type": "string", "description": "null si la revision pertenece a un estudiante autenticado."},
                "parent_review_id": {"type": "string", "format": "uuid", "description": "null si es una revision original (no una regeneracion)."},
                "language": {"type": "string"},
                "exercise": {"type": "string"},
                "level": {"type": "string"},
                "review_type": {"type": "string"},
                "student_code": {"type": "string"},
                "response": {"$ref": "#/definitions/ReviewResponse"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
    },
}


def create_app():
    configure_logging()

    app = Flask(__name__)
    app.config.from_object(get_config())

    CORS(
        app,
        origins=app.config["ALLOWED_ORIGINS"],
        supports_credentials=False,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "OPTIONS"],
    )

    limiter.init_app(app)

    Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)

    app.register_blueprint(review_bp)

    @app.route("/health", methods=["GET"])
    def health():
        """
        Chequeo de salud del servidor.
        ---
        tags:
          - Sistema
        summary: Chequeo de salud del servidor.
        description: No requiere autenticacion.
        responses:
          200:
            description: El servidor esta funcionando.
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
        """
        return jsonify({"status": "ok"})

    if app.config["DEBUG"]:
        @app.route("/api/_internal/test-crash", methods=["GET"])
        def _test_crash():
            """
            [Solo DEBUG] Fuerza una excepcion no controlada (para tests).
            ---
            tags:
              - Interno
            summary: Solo existe si DEBUG=True. Fuerza un crash para verificar que la respuesta siga siendo JSON.
            description: >
              Usado por tests/test_api_manual.py para confirmar que una excepcion no controlada
              devuelve JSON 500 (no el debugger HTML de Werkzeug) incluso con DEBUG=True. No existe
              cuando DEBUG=False (no se registra esta ruta en produccion).
            responses:
              500:
                description: Excepcion forzada, capturada por el errorhandler generico.
            """
            raise RuntimeError("Crash de prueba forzado (tests/test_api_manual.py).")

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Recurso no encontrado."}), 404

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "El cuerpo de la solicitud excede el tamano maximo permitido."}), 413

    @app.errorhandler(429)
    def rate_limited(_error):
        return jsonify({
            "error": (
                "Se alcanzo el limite de solicitudes de este backend para tu IP "
                "(no relacionado con la cuota de Gemini). Espera un momento e intenta de nuevo."
            )
        }), 429

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"error": "Error interno del servidor."}), 500

    @app.errorhandler(Exception)
    def unhandled_exception(error):
        # Los HTTPException (404/413/429/etc.) nunca llegan aca en la practica: Flask los
        # resuelve por codigo antes de caer en el handler generico. Este catch-all cubre
        # cualquier excepcion de Python no anticipada (bugs), y es lo que garantiza JSON
        # incluso con DEBUG=True: sin este handler, Flask deja que el debugger interactivo
        # de Werkzeug (HTML) tome esas excepciones en vez de pasar por @app.errorhandler(500).
        if isinstance(error, HTTPException):
            return error
        logger.exception("Excepcion no controlada: %s", error)
        return jsonify({"error": "Error interno del servidor."}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    # use_reloader=False: con el reloader activo, Werkzeug corre el pipeline en un
    # proceso hijo separado en Windows, y los logs de services/llm_connector.py
    # no llegan a la terminal donde se ejecuto "python app.py".
    app.run(debug=app.config["DEBUG"], use_reloader=False)
