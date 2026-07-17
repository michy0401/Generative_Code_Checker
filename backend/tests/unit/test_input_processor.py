"""Tests unitarios del Input Processor (services.llm_connector._process_input).

Sin red, sin servidor, sin Supabase ni Gemini reales: _process_input no tiene
dependencias externas, asi que se llama directamente.
"""

import pytest

import services.llm_connector as llm_connector

VALID_FIELDS = {
    "language": "Python",
    "exercise": "Crear una funcion que sume dos numeros.",
    "level": "Basico",
    "review_type": "Buenas practicas",
    "student_code": "def suma(a, b): return a + b",
}


def test_all_required_fields_present_returns_cleaned_dict():
    result = llm_connector._process_input(**VALID_FIELDS)
    assert result == {key: value.strip() for key, value in VALID_FIELDS.items()}


@pytest.mark.parametrize("missing_field", ["language", "exercise", "level", "review_type", "student_code"])
def test_missing_required_field_raises(missing_field):
    fields = dict(VALID_FIELDS)
    fields[missing_field] = None
    with pytest.raises(llm_connector.InputValidationError):
        llm_connector._process_input(**fields)


def test_empty_student_code_is_treated_as_missing_field():
    # Decision de diseno ya tomada (ver tests/test_api_manual.py, caso 5): un
    # student_code vacio/whitespace-only se trata igual que un campo faltante
    # (400), no como un caso valido de "codigo vacio" con 0 hallazgos.
    fields = dict(VALID_FIELDS)
    fields["student_code"] = "   "
    with pytest.raises(llm_connector.InputValidationError):
        llm_connector._process_input(**fields)


def test_student_code_exceeding_char_limit_raises_without_external_calls():
    fields = dict(VALID_FIELDS)
    fields["student_code"] = "x" * (llm_connector.MAX_STUDENT_CODE_CHARS + 1)
    with pytest.raises(llm_connector.InputValidationError):
        llm_connector._process_input(**fields)
