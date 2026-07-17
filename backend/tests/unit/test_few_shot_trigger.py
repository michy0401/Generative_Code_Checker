"""Tests unitarios del reintento condicional con Few-Shot Examples
(services.llm_connector.analizar_codigo).

Mockea _call_llm directamente (no _get_client/Gemini): sin red, sin servidor.
"""

from unittest.mock import patch

import pytest

import services.llm_connector as llm_connector

VALID_INPUT = {
    "language": "Python",
    "exercise": "Test few-shot",
    "level": "Basico",
    "review_type": "Buenas practicas",
    "student_code": "def f(): pass",
}


def _valid_data():
    return {
        "summary": {"language": "Python", "review_type": "Buenas practicas", "overall_assessment": "ok", "score": 80},
        "findings": [],
        "explanation": [],
        "suggested_code": {"improved_code": "def f(): pass", "changes_summary": []},
        "tests": [],
        "warnings": [],
    }


def test_second_attempt_with_few_shot_succeeds():
    invalid_data = {"summary": {"language": "Python"}}  # a proposito: faltan claves requeridas
    valid_data = _valid_data()

    with patch.object(llm_connector, "_call_llm", side_effect=[invalid_data, valid_data]) as mock_call:
        result = llm_connector.analizar_codigo(**VALID_INPUT)

    assert result == valid_data
    assert mock_call.call_count == 2

    first_prompt = mock_call.call_args_list[0].args[0]
    second_prompt = mock_call.call_args_list[1].args[0]
    assert "Ejemplo de referencia" not in first_prompt
    assert "Ejemplo de referencia" in second_prompt


def test_both_attempts_fail_raises_after_exactly_two_calls():
    invalid_data = {"summary": {"language": "Python"}}

    with patch.object(llm_connector, "_call_llm", side_effect=[invalid_data, invalid_data]) as mock_call:
        with pytest.raises(llm_connector.ResponseValidationError):
            llm_connector.analizar_codigo(**VALID_INPUT)

    assert mock_call.call_count == 2
