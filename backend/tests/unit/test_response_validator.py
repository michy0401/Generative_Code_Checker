"""Tests unitarios del Response Validator (services.llm_connector._validate_response).

Sin red, sin servidor, sin Supabase ni Gemini reales: _validate_response solo valida
un dict en memoria contra schemas/response_schema.json via jsonschema.
"""

import pytest

import services.llm_connector as llm_connector


def _valid_data():
    return {
        "summary": {
            "language": "Python",
            "review_type": "Buenas practicas",
            "overall_assessment": "Todo bien.",
            "score": 80,
        },
        "findings": [
            {
                "id": 1,
                "category": "Improvement",
                "severity": "Low",
                "title": "Ejemplo",
                "description": "Descripcion de ejemplo.",
                "line": 1,
            }
        ],
        "explanation": [
            {
                "finding_id": 1,
                "why": "Porque si.",
                "impact": "Ninguno.",
                "how_to_fix": "No hace falta.",
            }
        ],
        "suggested_code": {"improved_code": "def f(): pass", "changes_summary": []},
        "tests": [
            {"title": "t", "description": "d", "expected_result": "r"},
        ],
        "warnings": [],
    }


def test_valid_response_does_not_raise():
    llm_connector._validate_response(_valid_data())


def test_missing_required_field_raises():
    data = _valid_data()
    del data["findings"]
    with pytest.raises(llm_connector.ResponseValidationError):
        llm_connector._validate_response(data)


def test_invalid_enum_value_raises():
    data = _valid_data()
    data["findings"][0]["severity"] = "Critical"  # no es un valor valido del enum (High/Medium/Low)
    with pytest.raises(llm_connector.ResponseValidationError):
        llm_connector._validate_response(data)


@pytest.mark.parametrize("bad_score", [-5, 101, 1000])
def test_score_out_of_range_raises(bad_score):
    data = _valid_data()
    data["summary"]["score"] = bad_score
    with pytest.raises(llm_connector.ResponseValidationError):
        llm_connector._validate_response(data)
