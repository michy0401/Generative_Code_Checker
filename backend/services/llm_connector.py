"""
Modulo de IA - Sistema Inteligente de Revision de Codigo para Estudiantes.

Implementa el pipeline documentado en "Arquitectura del Modulo de IA y
Estrategia de Prompt Engineering" (v1.0):

    Input Processor -> Prompt Builder -> LLM Service -> Output Parser -> Response Validator

La unica funcion publica es `analizar_codigo`.
"""

import json
import logging
import os
import time

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import errors as genai_errors
# pyrefly: ignore [missing-import]
from google.genai import types as genai_types
from jsonschema import ValidationError as SchemaValidationError
from jsonschema import validate as validate_schema

load_dotenv()

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-flash-lite-latest"
GENERATION_CONFIG = {
    "temperature": 0.2,
    "top_p": 1.0,
    "max_output_tokens": 2000,
}

MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.5

REQUIRED_FIELDS = ["language", "exercise", "level", "review_type", "student_code"]

_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schemas", "response_schema.json")

with open(_SCHEMA_PATH, "r", encoding="utf-8") as _schema_file:
    RESPONSE_SCHEMA = json.load(_schema_file)

SYSTEM_PROMPT = """Actuas como un Ingeniero de Software Senior especializado en revision de \
codigo con enfoque educativo.

Reglas que debes seguir siempre:
- No afirmes que el codigo funciona ni que ha sido ejecutado.
- No asumas resultados de ejecucion: el codigo no se ejecuta en este proceso.
- Diferencia claramente entre errores, mejoras y recomendaciones.
- Explica cada hallazgo (por que ocurre, que impacto tiene y como corregirlo).
- Manten un lenguaje educativo, claro y respetuoso, pensado para un estudiante.
- No inventes informacion que no puedas sustentar con el codigo recibido.
- Evita cualquier contenido fuera del contexto de revision de codigo.
- Responde UNICAMENTE con un objeto JSON que cumpla de forma exacta el Response \
Schema entregado a continuacion. No agregues texto antes ni despues del JSON, ni \
uses bloques de markdown (```)."""


class InputValidationError(Exception):
    """Los datos recibidos del Backend no son validos."""


class LLMCommunicationError(Exception):
    """Fallo de comunicacion con el proveedor del LLM (red, parseo, etc.)."""


class QuotaExceededError(LLMCommunicationError):
    """La cuota de la API fue excedida (HTTP 429). No debe reintentarse."""


class ResponseValidationError(Exception):
    """La respuesta del modelo no cumple el Response Schema."""


def _process_input(language, exercise, level, review_type, student_code):
    """Input Processor: valida campos requeridos y normaliza el texto."""
    raw_fields = {
        "language": language,
        "exercise": exercise,
        "level": level,
        "review_type": review_type,
        "student_code": student_code,
    }

    missing = [
        name for name in REQUIRED_FIELDS
        if raw_fields.get(name) is None or not str(raw_fields[name]).strip()
    ]
    if missing:
        raise InputValidationError(
            f"Faltan campos requeridos o estan vacios: {', '.join(missing)}"
        )

    return {name: str(value).strip() for name, value in raw_fields.items()}


def _build_regeneration_context(previous_review, motivo_regeneracion):
    """Arma el bloque opcional de "revision anterior" / "motivo de regeneracion"
    (seccion 5.4 del documento de arquitectura). Vacio si no aplica (revision nueva)."""
    if previous_review is None and not motivo_regeneracion:
        return ""

    lines = [
        "\nEsta peticion es una REGENERACION de una revision anterior sobre el mismo "
        "ejercicio y codigo base. No repitas literalmente las mismas explicaciones si "
        "el codigo no cambio respecto a la revision anterior; si el codigo si cambio, "
        "evalua los cambios teniendo en cuenta lo que ya se habia senalado."
    ]

    if previous_review is not None:
        previous_assessment = previous_review.get("summary", {}).get("overall_assessment", "")
        previous_titles = [
            finding.get("title", "")
            for finding in previous_review.get("findings", [])
            if finding.get("title")
        ]
        lines.append(f"\nEvaluacion anterior: {previous_assessment}")
        if previous_titles:
            lines.append("Hallazgos senalados anteriormente: " + "; ".join(previous_titles))

    if motivo_regeneracion:
        lines.append(
            f'\nEl estudiante pidio esta nueva revision por el siguiente motivo: '
            f'"{motivo_regeneracion}". Abordalo explicitamente en el "overall_assessment" '
            f"o en el finding que corresponda."
        )

    return "\n".join(lines) + "\n"


def _build_prompt(inputs, previous_review=None, motivo_regeneracion=None):
    """Prompt Builder: combina variables, guardrails, el Response Schema y,
    cuando aplica, el contexto de regeneracion (revision anterior / motivo)."""
    schema_text = json.dumps(RESPONSE_SCHEMA, ensure_ascii=False, indent=2)
    regeneration_context = _build_regeneration_context(previous_review, motivo_regeneracion)

    return f"""{SYSTEM_PROMPT}

Response Schema (debes cumplirlo exactamente):
{schema_text}

Datos de la revision:
- Lenguaje: {inputs['language']}
- Ejercicio: {inputs['exercise']}
- Nivel academico: {inputs['level']}
- Tipo de revision: {inputs['review_type']}
{regeneration_context}
Codigo del estudiante:
{inputs['student_code']}
"""


def _clean_output_text(raw_text):
    """Output Parser: elimina backticks/markdown y texto sobrante alrededor del JSON."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
    text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LLMCommunicationError("La respuesta del modelo no contiene un objeto JSON valido.")

    return text[start:end + 1]


_client = None


def _get_client():
    """Autenticacion: crea el cliente de Gemini de forma perezosa (no al importar el modulo)."""
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise LLMCommunicationError(
                "GOOGLE_API_KEY no esta configurada. Copia .env.example a .env y completa la clave."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _call_llm(prompt):
    """LLM Service: envia el prompt a Gemini con reintentos ante errores transitorios."""
    config = genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=GENERATION_CONFIG["temperature"],
        top_p=GENERATION_CONFIG["top_p"],
        max_output_tokens=GENERATION_CONFIG["max_output_tokens"],
    )
    client = _get_client()

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME, contents=prompt, config=config
            )
            cleaned = _clean_output_text(response.text)
            return json.loads(cleaned)
        except genai_errors.APIError as error:
            if error.code == 429:
                raise QuotaExceededError(
                    "Cuota excedida: limite de solicitudes alcanzado. "
                    "Intenta nuevamente mas tarde."
                ) from error

            last_error = error
            logger.warning(
                "Intento %s/%s fallo al comunicarse con el LLM: %s",
                attempt, MAX_ATTEMPTS, error,
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
        except (LLMCommunicationError, json.JSONDecodeError) as error:
            last_error = error
            logger.warning(
                "Intento %s/%s fallo al parsear la respuesta del modelo: %s",
                attempt, MAX_ATTEMPTS, error,
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise LLMCommunicationError(
        f"No se pudo obtener una respuesta valida del modelo tras {MAX_ATTEMPTS} intentos: {last_error}"
    )


def _validate_response(data):
    """Response Validator: valida la respuesta contra schemas/response_schema.json."""
    try:
        validate_schema(instance=data, schema=RESPONSE_SCHEMA)
    except SchemaValidationError as error:
        location = ".".join(str(part) for part in error.absolute_path) or "raiz del objeto"
        logger.error(
            "❌ Response NO valida contra el schema: %s en '%s'", error.message, location
        )
        raise ResponseValidationError(
            f"La respuesta del modelo no cumple el formato esperado: {error.message} en '{location}'"
        ) from error
    else:
        logger.info("✅ Response validada correctamente contra response_schema.json")


def analizar_codigo(
    language, exercise, level, review_type, student_code,
    previous_review=None, motivo_regeneracion=None,
):
    """
    Punto de entrada publico del modulo de IA.

    Devuelve un diccionario que cumple exactamente `schemas/response_schema.json`
    (summary, findings, explanation, suggested_code, tests, warnings).

    `previous_review` (dict, la respuesta completa de una revision anterior) y
    `motivo_regeneracion` (texto libre) son opcionales - se usan solo cuando
    esta revision es una regeneracion de una revision existente (ver
    POST /api/reviews/<id>/regenerate). No cambian el Response Schema de salida.

    Lanza:
        InputValidationError: si faltan campos requeridos.
        QuotaExceededError: si la cuota del proveedor fue excedida.
        LLMCommunicationError: si falla la comunicacion o el parseo del modelo.
        ResponseValidationError: si la respuesta no cumple el Response Schema.
    """
    inputs = _process_input(language, exercise, level, review_type, student_code)
    prompt = _build_prompt(inputs, previous_review=previous_review, motivo_regeneracion=motivo_regeneracion)
    data = _call_llm(prompt)
    _validate_response(data)
    return data
