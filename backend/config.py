"""Configuracion de la aplicacion por entorno, cargada desde variables de .env."""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuracion base compartida por todos los entornos."""

    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    # Lista explicita de origenes permitidos para CORS (nunca "*": el sistema maneja JWT).
    ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]

    # Flask rechaza con 413 cualquier request cuyo body supere esto (ver @app.errorhandler(413)).
    # Default 100 KB: muy por encima de cualquier ejercicio de estudiante razonable.
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_REQUEST_SIZE_BYTES", 100 * 1024))

    # Limite de requests por IP a los endpoints que consumen cuota del LLM (/api/review,
    # /api/reviews/<id>/regenerate). Formato de flask-limiter (ej. "30 per minute").
    # El valor "correcto" depende de la cuota real del plan de Gemini en uso, por eso es
    # configurable en vez de una constante fija.
    REVIEW_RATE_LIMIT = os.getenv("REVIEW_RATE_LIMIT", "30 per minute")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


def get_config():
    return DevelopmentConfig if Config.FLASK_ENV == "development" else ProductionConfig
