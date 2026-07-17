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
    """
    Analiza codigo de un estudiante con IA y persiste el resultado.
    ---
    tags:
      - Revisiones
    summary: Analiza codigo de un estudiante con IA y persiste el resultado.
    description: >
      Ejecuta el pipeline completo (Input Processor -> Prompt Builder -> LLM Service ->
      Output Parser -> Response Validator) y guarda la revision en Supabase.
      Autenticacion OPCIONAL: si se manda un JWT valido de Supabase Auth, la revision
      queda asociada al estudiante (student_id); si no se manda ningun token, funciona
      en modo anonimo con session_id (se genera uno nuevo si no se envia).
    security:
      - Bearer: []
    parameters:
      - in: header
        name: Authorization
        type: string
        required: false
        description: "Opcional. 'Bearer <jwt>' de Supabase Auth."
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [language, exercise, level, review_type, student_code]
          properties:
            language:
              type: string
              example: Python
            exercise:
              type: string
              example: "Crear una funcion que sume dos numeros."
            level:
              type: string
              example: Basico
            review_type:
              type: string
              example: "Buenas practicas"
            student_code:
              type: string
              example: "def suma(a, b): return a + b"
            session_id:
              type: string
              description: Opcional. Si no se manda, se genera uno nuevo y se devuelve en la respuesta.
    responses:
      200:
        description: Analisis completado (y persistido si Supabase respondio bien).
        schema:
          $ref: '#/definitions/ReviewResponse'
      400:
        description: Faltan campos requeridos, o el body no es JSON valido.
      401:
        description: Se mando un Authorization Bearer, pero el token es invalido o expiro.
      502:
        description: Fallo la comunicacion con el LLM (Gemini) tras los reintentos, o se excedio la cuota.
      503:
        description: La respuesta del LLM no cumple el Response Schema.
    """
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
    """
    Historial de revisiones del estudiante autenticado.
    ---
    tags:
      - Revisiones
    summary: Historial de revisiones del estudiante autenticado.
    description: Autenticacion OBLIGATORIA (JWT de Supabase Auth).
    security:
      - Bearer: []
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: "'Bearer <jwt>' de Supabase Auth."
    responses:
      200:
        description: Revisiones del estudiante, ordenadas por created_at descendente. Vacia si no tiene ninguna.
        schema:
          type: array
          items:
            $ref: '#/definitions/ReviewRow'
      401:
        description: Falta el token, o es invalido/expirado.
      502:
        description: No se pudo consultar Supabase.
    """
    try:
        rows = review_repository.list_reviews_by_student(g.student_id)
    except review_repository.RepositoryError as error:
        return jsonify({"error": "No se pudo consultar Supabase.", "detalle": str(error)}), 502

    return jsonify(rows), 200


@review_bp.route("/api/reviews/<review_id>", methods=["GET"])
def get_review(review_id):
    """
    Devuelve una revision puntual por id.
    ---
    tags:
      - Revisiones
    summary: Devuelve una revision puntual por id.
    description: Publico, no requiere autenticacion.
    parameters:
      - in: path
        name: review_id
        type: string
        required: true
        description: UUID de la revision.
    responses:
      200:
        description: La revision encontrada.
        schema:
          $ref: '#/definitions/ReviewRow'
      404:
        description: No existe una revision con ese id.
      502:
        description: No se pudo consultar Supabase.
    """
    try:
        row = review_repository.get_review_by_id(review_id)
    except review_repository.RepositoryError as error:
        return jsonify({"error": "No se pudo consultar Supabase.", "detalle": str(error)}), 502

    if row is None:
        return jsonify({"error": "Revision no encontrada."}), 404

    return jsonify(row), 200


@review_bp.route("/api/reviews", methods=["GET"])
def list_reviews():
    """
    Historial de revisiones de una sesion anonima.
    ---
    tags:
      - Revisiones
    summary: Historial de revisiones de una sesion anonima.
    description: Publico, no requiere autenticacion.
    parameters:
      - in: query
        name: session_id
        type: string
        required: true
        description: session_id devuelto por POST /api/review.
    responses:
      200:
        description: Revisiones de esa sesion, ordenadas por created_at descendente. Vacia si no hay ninguna.
        schema:
          type: array
          items:
            $ref: '#/definitions/ReviewRow'
      400:
        description: Falta el parametro session_id.
      502:
        description: No se pudo consultar Supabase.
    """
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
    """
    Regenera una revision existente (nueva pasada de analisis).
    ---
    tags:
      - Revisiones
    summary: Regenera una revision existente (nueva pasada de analisis).
    description: >
      Reutiliza language/exercise/level/review_type de la revision original. Crea una
      fila NUEVA con parent_review_id apuntando a la original - nunca la sobrescribe.
      Autenticacion OPCIONAL (misma logica que POST /api/review), pero quien pide debe
      ser el dueno de la revision original (mismo student_id si es de un estudiante
      autenticado, o mismo session_id si es anonima).
    security:
      - Bearer: []
    parameters:
      - in: path
        name: review_id
        type: string
        required: true
        description: UUID de la revision a regenerar.
      - in: header
        name: Authorization
        type: string
        required: false
        description: Requerido solo si la revision original pertenece a un estudiante autenticado.
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            session_id:
              type: string
              description: Requerido si la revision original es anonima - debe coincidir exactamente.
            student_code:
              type: string
              description: Opcional. Si no se manda, se reusa el student_code de la revision original.
            motivo_regeneracion:
              type: string
              description: Opcional, texto libre explicando por que se pide la nueva revision.
    responses:
      200:
        description: Nueva revision generada y persistida.
        schema:
          $ref: '#/definitions/ReviewResponse'
      403:
        description: >
          Quien pide no es el dueno de la revision (session_id o student_id no coinciden).
          Mensaje generico, no revela si el review_id existe ni de quien es.
      404:
        description: No existe una revision con ese review_id.
      502:
        description: Fallo la comunicacion con el LLM, o con Supabase.
      503:
        description: La respuesta del LLM no cumple el Response Schema.
    """
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
    """
    Cadena completa de revisiones relacionadas (original + regeneraciones).
    ---
    tags:
      - Revisiones
    summary: Cadena completa de revisiones relacionadas (original + regeneraciones).
    description: Mismo ownership check que POST /api/reviews/{review_id}/regenerate.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: review_id
        type: string
        required: true
        description: UUID de cualquier revision de la cadena.
      - in: query
        name: session_id
        type: string
        required: false
        description: Requerido si la cadena es anonima - debe coincidir exactamente.
      - in: header
        name: Authorization
        type: string
        required: false
        description: Requerido solo si la cadena pertenece a un estudiante autenticado.
    responses:
      200:
        description: Todas las revisiones relacionadas (la original y sus regeneraciones), ordenadas por created_at.
        schema:
          type: array
          items:
            $ref: '#/definitions/ReviewRow'
      403:
        description: Quien pide no es el dueno de la revision. Mensaje generico.
      404:
        description: No existe una revision con ese review_id.
      502:
        description: No se pudo consultar Supabase.
    """
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
