"""Limitacion conocida y documentada (Parte C, item 4 de la tarea de pytest):
no es practico automatizar un test realista de "token realmente expirado".

El backend valida JWT de Supabase Auth contra las llaves asimetricas (ES256)
publicadas en el endpoint JWKS real del proyecto (middleware/auth.py) - no existe
ningun secreto compartido con el que este proceso de test pueda firmar un token
"valido" el mismo. Fabricar un JWT con `exp` vencido pero firmado con una clave de
prueba NO ejercita el camino real de expiracion: PyJWT lo rechazaria antes por firma
invalida / `kid` desconocido en el JWKS real, no por el claim `exp` - eso es
exactamente el mismo camino que ya cubre el caso 10 de tests/test_api_manual.py
("JWT invalido"), no el caso distinto de "firma valida pero vencido".

La unica forma de ejercitar el camino real seria conseguir un token real emitido
por Supabase (como en los casos 12/16 de tests/test_api_manual.py, via la Auth
Admin API) y esperar a que expire (~1 hora por default de Supabase) antes de
usarlo - no es practico como parte de un run automatizado de tests, ni de pytest
ni del script manual. Se documenta esto como limitacion conocida en vez de simular
un escenario que no refleja el comportamiento real del backend.
"""

import pytest


@pytest.mark.skip(
    reason=(
        "No se puede automatizar de forma realista: el backend valida JWT contra el "
        "JWKS real de Supabase (ES256), asi que un token 'expirado' fabricado en el "
        "test fallaria por firma invalida, no por expiracion, y no ejercitaria el "
        "camino real. Requeriria un token real emitido por Supabase y esperar a que "
        "expire (~1h), lo cual no es practico en un run automatizado. Ver el "
        "docstring de este modulo para el detalle completo."
    )
)
def test_expired_real_supabase_token_returns_401():
    """Placeholder documentado: requeriria un JWT real, vencido, emitido por Supabase."""
