"""Blueprint de metricas agregadas para el dashboard (RF-10).

Responsabilidad distinta a routes/review.py (analitica de todo el sistema, no
CRUD de una revision puntual), por eso vive en su propio blueprint.
"""

import logging

from flask import Blueprint, jsonify

import repositories.review_repository as review_repository

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
      estudiante particular. Una version "mis metricas" filtrada por student_id, si
      se necesita mas adelante, seria una tarea aparte.
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
