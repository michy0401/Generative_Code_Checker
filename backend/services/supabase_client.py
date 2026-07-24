"""Cliente unico de Supabase, reutilizado por toda la capa de repositorios.

Se crea de forma perezosa (no al importar el modulo) para que /health y el resto
de la app puedan arrancar aunque falten las variables de Supabase - recien falla
cuando algo intenta usarlo de verdad.
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
