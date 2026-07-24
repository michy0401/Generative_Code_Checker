"""Blueprint de metricas agregadas para el dashboard.

Vive aparte de routes/review.py: analitica de todo el sistema, no CRUD de una
revision puntual.
"""

import logging

from flask import Blueprint, g, jsonify

import repositories.review_repository as review_repository
from middleware.auth import require_auth

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/api/dashboard/metrics", methods=["GET"])
def get_dashboard_metrics():
    """
    Metricas agregadas del sistema para el dashboard (RF-10).
    ---
    tags:
      - Dashboard
    summary: Metricas agregadas del sistema para el dashboard (RF-10).
    description: >
      Publico, no requiere autenticacion: es un tablero agregado de TODO el sistema
      (todas las revisiones de todos los estudiantes y sesiones anonimas), no de un
      estudiante particular. Para metricas filtradas al estudiante autenticado, ver
      GET /api/dashboard/mine.
    responses:
      200:
        description: Metricas calculadas correctamente.
        schema:
          $ref: '#/definitions/DashboardMetrics'
      503:
        description: No se pudo consultar Supabase para calcular las metricas.
    """
    try:
        metrics = review_repository.get_dashboard_metrics()
    except review_repository.RepositoryError as error:
        return jsonify({
            "error": "No se pudieron calcular las metricas del dashboard.",
            "detalle": str(error),
        }), 503

    return jsonify(metrics), 200


@dashboard_bp.route("/api/dashboard/mine", methods=["GET"])
@require_auth
def get_dashboard_metrics_mine():
    """
    Metricas agregadas de las revisiones del estudiante autenticado (RF-10, "Mis metricas").
    ---
    tags:
      - Dashboard
    summary: Metricas agregadas de las revisiones del estudiante autenticado.
    description: >
      Autenticacion OBLIGATORIA (JWT de Supabase Auth) - a diferencia de
      GET /api/dashboard/metrics (publico, agrega TODO el sistema), este endpoint
      agrega solo las revisiones cuyo student_id coincide con el `sub` del token; el
      student_id sale unicamente del JWT, nunca de un parametro. Si el estudiante
      todavia no tiene ninguna revision, devuelve las 5 metricas en cero/vacias, no
      un error.
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
        description: Metricas del estudiante calculadas correctamente (en cero si no tiene revisiones).
        schema:
          $ref: '#/definitions/DashboardMetrics'
      401:
        description: Falta el token, o es invalido/expirado.
      503:
        description: No se pudo consultar Supabase para calcular las metricas.
    """
    try:
        metrics = review_repository.get_dashboard_metrics_for_student(g.student_id)
    except review_repository.RepositoryError as error:
        return jsonify({
            "error": "No se pudieron calcular las metricas del dashboard.",
            "detalle": str(error),
        }), 503

    return jsonify(metrics), 200
