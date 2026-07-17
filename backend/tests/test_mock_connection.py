"""
Prueba de la forma de respuesta sin depender de conexion a internet.

`analizar_codigo_mock` simula lo que devolveria `services.llm_connector.analizar_codigo`,
cumpliendo el mismo Response Schema, para que ambas funciones sean intercambiables
en el resto del backend.
"""

import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jsonschema import validate as validate_schema

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schemas", "response_schema.json")

with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
    RESPONSE_SCHEMA = json.load(schema_file)


def analizar_codigo_mock(language, exercise, level, review_type, student_code):
    """Simula la respuesta de analizar_codigo cumpliendo response_schema.json."""
    return {
        "summary": {
            "language": language,
            "review_type": review_type,
            "overall_assessment": "Revision simulada con fines de prueba.",
            "score": 80,
        },
        "findings": [
            {
                "id": 1,
                "category": "Improvement",
                "severity": "Low",
                "title": "Agregar type hints",
                "description": "Los parametros de la funcion no tienen anotaciones de tipo.",
                "line": 1,
            }
        ],
        "explanation": [
            {
                "finding_id": 1,
                "why": "Las anotaciones de tipo ayudan a documentar el contrato de la funcion.",
                "impact": "Bajo: no afecta el comportamiento, solo la mantenibilidad.",
                "how_to_fix": "Agregar anotaciones como 'def suma(a: int, b: int) -> int:'.",
            }
        ],
        "suggested_code": {
            "improved_code": student_code,
            "changes_summary": ["Se sugieren type hints (respuesta simulada)."],
        },
        "tests": [
            {
                "title": "Prueba basica",
                "description": "Verificar el comportamiento con valores simples.",
                "expected_result": "El resultado debe coincidir con el esperado (a validar en un entorno real).",
            }
        ],
        "warnings": [
            "Esta es una respuesta simulada (mock); no proviene de un modelo de IA real.",
            f"Nivel declarado: {level}. El codigo debe ser validado en un entorno de ejecucion real.",
        ],
    }


def test_mock_response_matches_schema():
    resultado = analizar_codigo_mock(
        language="Python",
        exercise="Crear una funcion que sume dos numeros.",
        level="Basico",
        review_type="Buenas practicas",
        student_code="def suma(a, b): return a + b",
    )
    validate_schema(instance=resultado, schema=RESPONSE_SCHEMA)
    return resultado


if __name__ == "__main__":
    resultado = test_mock_response_matches_schema()
    print("Conexion simulada exitosa. La respuesta cumple response_schema.json.")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
