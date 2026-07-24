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


# --- review_type controlado -------------------------------------------------------

@pytest.mark.parametrize("review_type", llm_connector.ALLOWED_REVIEW_TYPES)
def test_valid_review_type_passes(review_type):
    fields = dict(VALID_FIELDS)
    fields["review_type"] = review_type
    result = llm_connector._process_input(**fields)
    assert result["review_type"] == review_type


@pytest.mark.parametrize("review_type", ["ERRORES", "  Legibilidad  ", "Seguridad Básica"])
def test_valid_review_type_is_case_and_accent_insensitive(review_type):
    # Normalizacion: mayusculas/minusculas, tildes y espacios de mas no deben
    # rechazar un valor que de otro modo es correcto.
    fields = dict(VALID_FIELDS)
    fields["review_type"] = review_type
    llm_connector._process_input(**fields)  # no debe lanzar


def test_invalid_review_type_raises_with_allowed_values_in_message():
    fields = dict(VALID_FIELDS)
    fields["review_type"] = "cositas raras"
    with pytest.raises(llm_connector.InputValidationError) as exc_info:
        llm_connector._process_input(**fields)

    message = str(exc_info.value)
    assert "cositas raras" in message
    for allowed in llm_connector.ALLOWED_REVIEW_TYPES:
        assert allowed in message
