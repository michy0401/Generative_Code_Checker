"""Extensiones de Flask compartidas entre app.py y los blueprints.

Vive en su propio modulo (en vez de crearse dentro de app.py) para que
routes/review.py pueda importar `limiter` y decorar sus vistas sin generar
un import circular con app.py (que a su vez importa routes/review.py).
"""

# pyrefly: ignore [missing-import]
from flask_limiter import Limiter
# pyrefly: ignore [missing-import]
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
