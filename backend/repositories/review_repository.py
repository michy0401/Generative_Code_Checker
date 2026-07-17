"""Capa de acceso a datos para la tabla `reviews` de Supabase.

Ninguna otra parte del backend debe hablar directo con el cliente de Supabase:
todo el acceso a `reviews` pasa por estas funciones.
"""

import logging

from services.supabase_client import get_client

logger = logging.getLogger(__name__)

TABLE = "reviews"


class RepositoryError(Exception):
    """Fallo al comunicarse con Supabase (red, credenciales invalidas, o error de la API)."""


def create_review(
    language, exercise, level, review_type, student_code, response,
    student_id=None, session_id=None, parent_review_id=None,
):
    """Inserta una revision y devuelve la fila creada (incluyendo su id).

    `parent_review_id` queda en None para revisiones originales, o apunta a
    la revision anterior cuando esta es una regeneracion. Se omite del
    payload cuando es None (en vez de mandarlo como NULL explicito) para que
    /api/review siga funcionando igual en un entorno donde todavia no se
    corrio migrations/002_add_parent_review.sql - Postgrest rechaza el
    insert completo si el payload trae una clave que no es una columna real.
    """
    payload = {
        "student_id": student_id,
        "session_id": session_id,
        "language": language,
        "exercise": exercise,
        "level": level,
        "review_type": review_type,
        "student_code": student_code,
        "response": response,
    }
    if parent_review_id is not None:
        payload["parent_review_id"] = parent_review_id
    try:
        result = get_client().table(TABLE).insert(payload).execute()
    except Exception as error:
        logger.error("No se pudo guardar la revision en Supabase: %s", error)
        raise RepositoryError(str(error)) from error

    if not result.data:
        message = "Supabase no devolvio la fila insertada al crear la revision."
        logger.error(message)
        raise RepositoryError(message)

    return result.data[0]


def get_review_by_id(review_id):
    """Devuelve una revision puntual, o None si no existe."""
    try:
        result = get_client().table(TABLE).select("*").eq("id", review_id).limit(1).execute()
    except Exception as error:
        logger.error("No se pudo consultar la revision %s en Supabase: %s", review_id, error)
        raise RepositoryError(str(error)) from error

    return result.data[0] if result.data else None


def list_reviews_by_session(session_id):
    """Devuelve el historial de revisiones de una sesion anonima, mas recientes primero."""
    try:
        result = (
            get_client()
            .table(TABLE)
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as error:
        logger.error("No se pudo listar revisiones de la sesion %s en Supabase: %s", session_id, error)
        raise RepositoryError(str(error)) from error

    return result.data or []


def list_reviews_by_student(student_id):
    """Devuelve el historial de revisiones de un estudiante autenticado, mas recientes primero."""
    try:
        result = (
            get_client()
            .table(TABLE)
            .select("*")
            .eq("student_id", student_id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as error:
        logger.error("No se pudo listar revisiones del estudiante %s en Supabase: %s", student_id, error)
        raise RepositoryError(str(error)) from error

    return result.data or []


def list_review_history(review_id):
    """Devuelve la cadena completa de revisiones relacionadas con `review_id`
    (la revision original y todas sus regeneraciones), ordenadas por created_at.

    Devuelve None si `review_id` no existe. Soporta cadenas de cualquier
    profundidad (regenerar una regeneracion): primero sube por
    `parent_review_id` hasta encontrar la revision original, y despues baja
    recolectando todos los descendientes con busquedas por niveles (no hace
    falta una consulta recursiva del lado de la base de datos para el volumen
    esperado de iteraciones por revision).
    """
    review = get_review_by_id(review_id)
    if review is None:
        return None

    root = review
    visited_ids = {review["id"]}
    while root.get("parent_review_id") and root["parent_review_id"] not in visited_ids:
        parent = get_review_by_id(root["parent_review_id"])
        if parent is None:
            break
        visited_ids.add(parent["id"])
        root = parent

    chain = {root["id"]: root}
    frontier = [root["id"]]
    while frontier:
        try:
            result = get_client().table(TABLE).select("*").in_("parent_review_id", frontier).execute()
        except Exception as error:
            logger.error("No se pudo reconstruir el historial de la revision %s en Supabase: %s", review_id, error)
            raise RepositoryError(str(error)) from error

        frontier = []
        for row in result.data or []:
            if row["id"] not in chain:
                chain[row["id"]] = row
                frontier.append(row["id"])

    return sorted(chain.values(), key=lambda row: row["created_at"])
