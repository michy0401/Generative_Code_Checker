"""Test unitario: si Supabase falla al guardar pero el LLM si respondio, el
endpoint debe devolver 200 igual con el analisis (el usuario no pierde su
resultado) y loguear el fallo de persistencia.

Usa el test client de Flask (create_app() en memoria, sin levantar el servidor)
y mockea tanto analizar_codigo (para no gastar cuota real de Gemini) como
repositories.review_repository.create_review (para simular la falla de Supabase).
create_app() no requiere ninguna variable de entorno real: todos los clientes
externos (Gemini, Supabase, JWKS) son perezosos y no se tocan en este test
porque el request no manda Authorization y ambas llamadas externas estan mockeadas.
"""

from unittest.mock import patch

import app as app_module
import repositories.review_repository as review_repository


def _valid_data():
    return {
        "summary": {
            "language": "Python",
            "review_type": "Buenas practicas",
            "overall_assessment": "Analisis de prueba (fallo de persistencia simulado).",
            "score": 80,
        },
        "findings": [],
        "explanation": [],
        "suggested_code": {"improved_code": "def f(): pass", "changes_summary": []},
        "tests": [],
        "warnings": [],
    }


def test_persistence_failure_still_returns_200_with_analysis(caplog):
    flask_app = app_module.create_app()
    client = flask_app.test_client()

    payload = {
        "language": "Python",
        "exercise": "Test fallo de persistencia",
        "level": "Basico",
        "review_type": "Buenas practicas",
        "student_code": "def f(): pass",
    }
    valid_data = _valid_data()

    # analizar_codigo() devuelve (data, prompt_sent) - el mock debe reflejar esa tupla.
    with patch("routes.review.analizar_codigo", return_value=(valid_data, "prompt de prueba")):
        with patch.object(
            review_repository, "create_review",
            side_effect=review_repository.RepositoryError("Supabase caido (simulado)"),
        ):
            with caplog.at_level("ERROR"):
                response = client.post("/api/review", json=payload)

    assert response.status_code == 200

    data = response.get_json()
    assert data["review_id"] is None
    assert data["summary"] == valid_data["summary"]
    assert data["findings"] == valid_data["findings"]

    assert any(
        "no se pudo persistir" in record.message.lower()
        for record in caplog.records
    ), f"no se encontro el log del fallo de persistencia; logs capturados: {[r.message for r in caplog.records]}"
