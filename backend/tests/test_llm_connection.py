"""
Prueba de conexion real con el LLM configurado (requiere GOOGLE_API_KEY valida en .env
y conexion a internet).
"""

import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm_connector import (
    InputValidationError,
    LLMCommunicationError,
    ResponseValidationError,
    analizar_codigo,
)


def ejecutar_prueba():
    print("--- Probando conexion con Gemini (gemini-2.0-flash-lite) ---")
    try:
        resultado = analizar_codigo(
            language="Python",
            exercise="Crear una funcion que sume dos numeros.",
            level="Basico",
            review_type="Buenas practicas",
            student_code="def suma(a, b): return a + b",
        )
    except InputValidationError as error:
        print(f"Fallo de validacion de entrada: {error}")
        return
    except ResponseValidationError as error:
        print(f"La respuesta del modelo no cumple el schema: {error}")
        return
    except LLMCommunicationError as error:
        print(f"Fallo en la comunicacion con el LLM: {error}")
        return

    print("Exito: conexion establecida y respuesta valida recibida.")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    ejecutar_prueba()
