"""Cliente unico de Supabase, reutilizado por toda la capa de repositorios.

Se crea de forma perezosa (no al importar el modulo): construir el cliente sin
SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY configuradas falla inmediatamente, y no
queremos que eso tumbe el arranque de la app (por ejemplo /health) si faltan
esas variables - solo debe fallar, de forma controlada, cuando algo realmente
intenta usar Supabase.
"""

import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

_client = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY deben estar configuradas en .env"
            )
        _client = create_client(url, key)
    return _client
