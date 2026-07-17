"""Tests unitarios de las metricas del dashboard (RF-10).

Mockea get_client() (sin Supabase real, sin red): construye filas falsas y confirma
que repositories.review_repository.get_dashboard_metrics() agrega correctamente, y
que la ruta devuelve 503 en JSON (no crashea) si Supabase falla.
"""

from unittest.mock import MagicMock, patch

import pytest

import app as app_module
import repositories.review_repository as review_repository


def _fake_row(language, status, parent_review_id, finding_titles):
    return {
        "language": language,
        "status": status,
        "parent_review_id": parent_review_id,
        "response": {"findings": [{"title": title} for title in finding_titles]},
    }


def _mock_select_result(rows):
    fake_result = MagicMock()
    fake_result.data = rows
    fake_client = MagicMock()
    fake_client.table.return_value.select.return_value.execute.return_value = fake_result
    return fake_client


def test_get_dashboard_metrics_aggregates_correctly():
    rows = [
        _fake_row("Python", "pending", None, ["Falta docstring", "Sin type hints"]),
        _fake_row("Python", "accepted", "parent-1", ["Falta docstring"]),
        _fake_row("JavaScript", "discarded", None, ["Uso de var en vez de let"]),
        _fake_row("Python", "accepted", None, ["Falta docstring", "Falta docstring"]),
    ]

    with patch.object(review_repository, "get_client", return_value=_mock_select_result(rows)):
        metrics = review_repository.get_dashboard_metrics()

    assert metrics["total_reviews"] == 4
    assert metrics["reviews_by_language"] == {"Python": 3, "JavaScript": 1}
    assert metrics["reviews_by_status"] == {"pending": 1, "accepted": 2, "discarded": 1}
    assert metrics["regenerated_count"] == 1

    findings_by_title = {item["title"]: item["count"] for item in metrics["most_frequent_findings"]}
    assert findings_by_title["Falta docstring"] == 4
    assert findings_by_title["Sin type hints"] == 1
    assert findings_by_title["Uso de var en vez de let"] == 1


def test_get_dashboard_metrics_returns_top_10_findings_in_order():
    rows = []
    for i in range(15):
        title = f"Hallazgo {i}"
        occurrences = 15 - i  # Hallazgo 0 aparece 15 veces, ..., Hallazgo 14 aparece 1 vez
        for _ in range(occurrences):
            rows.append(_fake_row("Python", "pending", None, [title]))

    with patch.object(review_repository, "get_client", return_value=_mock_select_result(rows)):
        metrics = review_repository.get_dashboard_metrics()

    most_frequent = metrics["most_frequent_findings"]
    assert len(most_frequent) == 10
    assert [item["title"] for item in most_frequent] == [f"Hallazgo {i}" for i in range(10)]
    assert most_frequent[0]["count"] == 15
    assert most_frequent[9]["count"] == 6


def test_get_dashboard_metrics_empty_table():
    with patch.object(review_repository, "get_client", return_value=_mock_select_result([])):
        metrics = review_repository.get_dashboard_metrics()

    assert metrics == {
        "total_reviews": 0,
        "reviews_by_language": {},
        "reviews_by_status": {},
        "regenerated_count": 0,
        "most_frequent_findings": [],
    }


def test_get_dashboard_metrics_raises_repository_error_on_failure():
    fake_client = MagicMock()
    fake_client.table.return_value.select.return_value.execute.side_effect = Exception("Supabase caido (simulado)")

    with patch.object(review_repository, "get_client", return_value=fake_client):
        with pytest.raises(review_repository.RepositoryError):
            review_repository.get_dashboard_metrics()


def test_dashboard_route_returns_503_json_on_repository_error():
    flask_app = app_module.create_app()
    client = flask_app.test_client()

    with patch.object(
        review_repository, "get_dashboard_metrics",
        side_effect=review_repository.RepositoryError("Supabase caido (simulado)"),
    ):
        response = client.get("/api/dashboard/metrics")

    assert response.status_code == 503
    data = response.get_json()
    assert "error" in data
