"""Configuracion centralizada de logging para toda la aplicacion.

Se llama una sola vez desde app.py. El resto de los modulos (por ejemplo
services/llm_connector.py) solo usan `logging.getLogger(__name__)` y sus
mensajes se propagan al handler configurado aqui - no hay que reconfigurar
logging en cada archivo.
"""

import logging
import sys


def configure_logging(level=logging.INFO):
    """Configura el root logger. Idempotente: no agrega handlers duplicados."""
    root = logging.getLogger()
    if root.handlers:
        return

    # Evita UnicodeEncodeError en consolas de Windows que no usan UTF-8 por defecto
    # (necesario para poder loggear simbolos como los usados en el Response Validator).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )

    root.addHandler(handler)
    root.setLevel(level)
