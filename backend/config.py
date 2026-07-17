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


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


def get_config():
    return DevelopmentConfig if Config.FLASK_ENV == "development" else ProductionConfig
