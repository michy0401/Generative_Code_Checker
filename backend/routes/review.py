"""Blueprint con los endpoints de revision de codigo."""

import logging
import uuid

from flask import Blueprint, g, jsonify, request

import repositories.review_repository as review_repository
import services.review_ownership as review_ownership
from middleware.auth import optional_auth, require_auth
from services.llm_connector import (
    InputValidationError,
    LLMCommunicationError,
    ResponseValidationError,
    analizar_codigo,
)

OWNERSHIP_ERROR = "No tenes permiso para regenerar esta revision"
HISTORY_OWNERSHIP_ERROR = "No tenes permiso para acceder a esta revision"

logger = logging.getLogger(__name__)

review_bp = Blueprint("review", __name__)


@review_bp.route("/api/review", methods=["POST"])
@optional_auth
def review_code():
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "El cuerpo de la solicitud debe ser un JSON valido."}), 400

    session_id = payload.get("session_id") or str(uuid.uuid4())
    # g.student_id lo resuelve @optional_auth: None en modo anonimo, o el
    # `sub` del JWT si el request trae uno valido (Supabase Auth).
    student_id = g.student_id

    try:
        resultado = analizar_codigo(
            language=payload.get("language"),
            exercise=payload.get("exercise"),
            level=payload.get("level"),
            review_type=payload.get("review_type"),
            student_code=payload.get("student_code"),
        )
    except InputValidationError as error:
        return jsonify({"error": str(error)}), 400

    except ResponseValidationError as error:
        return jsonify({"error": "La respuesta del modelo no cumple el formato esperado.", "detalle": str(error)}), 503

    except LLMCommunicationError as error:
        return jsonify({"error": "No se pudo completar la comunicacion con el servicio de IA.", "detalle": str(error)}), 502

    review_id = None
    try:
        row = review_repository.create_review(
            language=payload.get("language"),
            exercise=payload.get("exercise"),
            level=payload.get("level"),
            review_type=payload.get("review_type"),
            student_code=payload.get("student_code"),
            response=resultado,
            student_id=student_id,
            session_id=session_id,
        )
        review_id = row["id"]
    except review_repository.RepositoryError as error:
        # El analisis ya esta hecho: el usuario no debe perderlo solo porque
        # fallo la persistencia. Se devuelve igual, sin review_id.
        logger.error(
            "La revision no se pudo persistir en Supabase; se devuelve el analisis igual. Detalle: %s",
            error,
        )

    return jsonify({"review_id": review_id, "session_id": session_id, **resultado}), 200


@review_bp.route("/api/reviews/mine", methods=["GET"])
@require_auth
def list_my_reviews():
    try:
        rows = review_repository.list_reviews_by_student(g.student_id)
    except review_repository.RepositoryError as error:
        return jsonify({"error": "No se pudo consultar Supabase.", "detalle": str(error)}), 502

    return jsonify(rows), 200


@review_bp.route("/api/reviews/<review_id>", methods=["GET"])
def get_review(review_id):
    try:
        row = review_repository.get_review_by_id(review_id)
    except review_repository.RepositoryError as error:
        return jsonify({"error": "No se pudo consultar Supabase.", "detalle": str(error)}), 502

    if row is None:
        return jsonify({"error": "Revision no encontrada."}), 404

    return jsonify(row), 200


@review_bp.route("/api/reviews", methods=["GET"])
def list_reviews():
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "El parametro 'session_id' es requerido."}), 400

    try:
        rows = review_repository.list_reviews_by_session(session_id)
    except review_repository.RepositoryError as error:
        return jsonify({"error": "No se pudo consultar Supabase.", "detalle": str(error)}), 502

    return jsonify(rows), 200


@review_bp.route("/api/reviews/<review_id>/regenerate", methods=["POST"])
@optional_auth
def regenerate_review(review_id):
    try:
        original = review_repository.get_review_by_id(review_id)
    except review_repository.RepositoryError as error:
        return jsonify({"error": "No se pudo consultar Supabase.", "detalle": str(error)}), 502

    if original is None:
        return jsonify({"error": "Revision no encontrada."}), 404

    payload = request.get_json(silent=True) or {}

    if not review_ownership.is_owner(original, student_id=g.student_id, session_id=payload.get("session_id")):
        return jsonify({"error": OWNERSHIP_ERROR}), 403

    student_code = payload.get("student_code") or original.get("student_code")
    motivo_regeneracion = payload.get("motivo_regeneracion")

    try:
        resultado = analizar_codigo(
            language=original.get("language"),
            exercise=original.get("exercise"),
            level=original.get("level"),
            review_type=original.get("review_type"),
            student_code=student_code,
            previous_review=original.get("response"),
            motivo_regeneracion=motivo_regeneracion,
        )
    except InputValidationError as error:
        return jsonify({"error": str(error)}), 400

    except ResponseValidationError as error:
        return jsonify({"error": "La respuesta del modelo no cumple el formato esperado.", "detalle": str(error)}), 503

    except LLMCommunicationError as error:
        return jsonify({"error": "No se pudo completar la comunicacion con el servicio de IA.", "detalle": str(error)}), 502

    new_review_id = None
    try:
        row = review_repository.create_review(
            language=original.get("language"),
            exercise=original.get("exercise"),
            level=original.get("level"),
            review_type=original.get("review_type"),
            student_code=student_code,
            response=resultado,
            student_id=original.get("student_id"),
            session_id=original.get("session_id"),
            parent_review_id=original["id"],
        )
        new_review_id = row["id"]
    except review_repository.RepositoryError as error:
        logger.error(
            "La regeneracion no se pudo persistir en Supabase; se devuelve el analisis igual. Detalle: %s",
            error,
        )

    return jsonify({
        "review_id": new_review_id,
        "parent_review_id": original["id"],
        "session_id": original.get("session_id"),
        **resultado,
    }), 200


@review_bp.route("/api/reviews/<review_id>/history", methods=["GET"])
@optional_auth
def review_history(review_id):
    try:
        original = review_repository.get_review_by_id(review_id)
    except review_repository.RepositoryError as error:
        return jsonify({"error": "No se pudo consultar Supabase.", "detalle": str(error)}), 502

    if original is None:
        return jsonify({"error": "Revision no encontrada."}), 404

    session_id = request.args.get("session_id")
    if not review_ownership.is_owner(original, student_id=g.student_id, session_id=session_id):
        return jsonify({"error": HISTORY_OWNERSHIP_ERROR}), 403

    try:
        chain = review_repository.list_review_history(review_id)
    except review_repository.RepositoryError as error:
        return jsonify({"error": "No se pudo consultar Supabase.", "detalle": str(error)}), 502

    return jsonify(chain), 200
