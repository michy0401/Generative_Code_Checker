"""Tests unitarios del loop de reintentos por fallas transitorias
(services.llm_connector._call_llm), incluyendo el punto de la auditoria que solo
se habia verificado a mano: un error generico (no-429) reintenta exactamente
MAX_ATTEMPTS veces antes de fallar.

Mockea _get_client (no hay red real).
"""

from unittest.mock import MagicMock, patch

import pytest
# pyrefly: ignore [missing-import]
from google.genai import errors as genai_errors

import services.llm_connector as llm_connector


def test_generic_error_retries_exactly_max_attempts_then_raises():
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = genai_errors.APIError(
        500, {"error": {"message": "Internal error", "status": "INTERNAL"}}
    )

    with patch.object(llm_connector, "_get_client", return_value=fake_client):
        with patch.object(llm_connector.time, "sleep", return_value=None):  # no dormir de verdad en el test
            with pytest.raises(llm_connector.LLMCommunicationError):
                llm_connector._call_llm("prompt de prueba")

    assert fake_client.models.generate_content.call_count == llm_connector.MAX_ATTEMPTS


def test_quota_error_429_does_not_retry():
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = genai_errors.APIError(
        429, {"error": {"message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"}}
    )

    with patch.object(llm_connector, "_get_client", return_value=fake_client):
        with pytest.raises(llm_connector.QuotaExceededError):
            llm_connector._call_llm("prompt de prueba")

    assert fake_client.models.generate_content.call_count == 1
