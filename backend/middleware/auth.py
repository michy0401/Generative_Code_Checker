"""Validacion de JWT de Supabase Auth.

El backend no emite ni gestiona estos tokens - el login vive 100% en el
frontend, hablando directo con supabase-js (signUp / signInWithPassword).
Aca solo se valida la firma del JWT que el frontend manda (si lo manda) y se
extrae el id del estudiante (`sub`).

Este proyecto de Supabase usa el modelo nuevo de llaves asimetricas (ECC
P-256, algoritmo ES256) - no HS256 con secreto compartido. No hay ningun
secreto que guardar en .env: la verificacion se hace contra la llave publica
del proyecto, publicada en el endpoint JWKS de Supabase Auth
(`${SUPABASE_URL}/auth/v1/.well-known/jwks.json`, confirmado contra el
dashboard: responde 200 sin necesitar apikey, a diferencia de `/auth/v1/jwks`
que exige uno y no es el endpoint correcto). No se llama a la API de
Supabase con credenciales para esto.
"""

import logging
import os
from functools import wraps

import jwt
from dotenv import load_dotenv
from flask import g, jsonify, request

load_dotenv()

logger = logging.getLogger(__name__)

ALGORITHM = "ES256"
AUDIENCE = "authenticated"

_jwk_client = None


def _get_jwk_client():
    """Crea el PyJWKClient una sola vez (no en cada request) y lo reutiliza.

    PyJWKClient no hace ninguna llamada de red al construirse - solo valida
    el esquema de la URL - asi que esto es seguro de correr aunque
    SUPABASE_URL este mal configurada; el JWKS recien se descarga (y se
    cachea internamente, ver `cache_jwk_set` por defecto) la primera vez que
    se valida un token.
    """
    global _jwk_client
    if _jwk_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        if not supabase_url:
            raise RuntimeError("SUPABASE_URL debe estar configurada en .env para validar JWT.")
        jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwk_client = jwt.PyJWKClient(jwks_url)
    return _jwk_client


class InvalidTokenError(Exception):
    """El request trae un Authorization: Bearer <token> invalido o expirado."""


def _extract_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header[len("Bearer "):].strip()
    return token or None


def get_current_student_id():
    """Devuelve el student_id (uuid, claim `sub`) del JWT del request, o None si no hay token.

    No trata un token roto como anonimo: si el header viene pero no valida
    (firma incorrecta, expirado, llave/`kid` no encontrada, o el JWKS
    endpoint de Supabase no responde), lanza InvalidTokenError para que el
    caller responda 401 en vez de silenciarlo.
    """
    token = _extract_token()
    if token is None:
        return None

    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(token, signing_key.key, algorithms=[ALGORITHM], audience=AUDIENCE)
    except RuntimeError as error:
        logger.error("No se pudo validar el JWT: %s", error)
        raise InvalidTokenError("El servidor no tiene configurada la validacion de tokens.") from error
    except jwt.exceptions.PyJWKClientConnectionError as error:
        # Distinto de un token invalido: el JWKS endpoint de Supabase no
        # respondio (caido, timeout, red). No hay forma de confirmar el
        # token, asi que se trata como invalido igual, pero se loguea
        # aparte para poder diferenciarlo de un token simplemente roto.
        logger.error("No se pudo contactar el JWKS endpoint de Supabase para validar el JWT: %s", error)
        raise InvalidTokenError("Token invalido o expirado.") from error
    except jwt.PyJWTError as error:
        logger.warning("JWT invalido o expirado: %s", error)
        raise InvalidTokenError("Token invalido o expirado.") from error

    student_id = claims.get("sub")
    if not student_id:
        raise InvalidTokenError("El token no contiene un 'sub' valido.")

    return student_id


def optional_auth(view):
    """Resuelve g.student_id antes de la vista (None si no hay token).

    Si viene un token pero es invalido/expirado, corta con 401 antes de
    llegar a la vista - un token roto no se trata como anonimo.
    """
    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            g.student_id = get_current_student_id()
        except InvalidTokenError as error:
            return jsonify({"error": str(error)}), 401
        return view(*args, **kwargs)

    return wrapper


def require_auth(view):
    """Exige un JWT valido. Corta con 401 si falta o es invalido."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            student_id = get_current_student_id()
        except InvalidTokenError as error:
            return jsonify({"error": str(error)}), 401

        if student_id is None:
            return jsonify({"error": "Se requiere autenticacion."}), 401

        g.student_id = student_id
        return view(*args, **kwargs)

    return wrapper
