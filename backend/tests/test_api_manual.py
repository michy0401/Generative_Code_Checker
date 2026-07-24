"""
Script standalone de pruebas manuales contra el servidor real.

Uso:
    1. En una terminal: python app.py
    2. En otra terminal: python tests/test_api_manual.py

No es un test de pytest: es un vistazo rapido de 30 casos mientras se
desarrolla, pensado para correrse a mano contra el servidor local. Para tests
unitarios rapidos, sin servidor ni credenciales reales, ver tests/unit/ (correr
con "pytest" desde la raiz de backend/).
"""

import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Evita UnicodeEncodeError al imprimir ✅/❌ en consolas de Windows que no usan UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        # pyrefly: ignore [missing-import]
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# pyrefly: ignore [missing-import]
from google.genai import errors as genai_errors
# pyrefly: ignore [missing-import]
from supabase import create_client

import services.llm_connector as llm_connector

BASE_URL = "http://127.0.0.1:5000"
REVIEW_URL = f"{BASE_URL}/api/review"
SCHEMA_KEYS = {"summary", "findings", "explanation", "suggested_code", "tests", "warnings"}

TOTAL_CASES = 31
results = []  # (index, label, ok, detail)


def post(url, body_bytes, headers=None):
    """POST crudo via urllib. Devuelve (status_code, texto_de_respuesta)."""
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=body_bytes, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")


def post_json(url, payload, headers=None):
    return post(url, json.dumps(payload).encode("utf-8"), headers=headers)


def get(url, headers=None):
    """GET crudo via urllib. Devuelve (status_code, texto_de_respuesta)."""
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")


def patch_json(url, payload, headers=None):
    """PATCH crudo via urllib. Devuelve (status_code, texto_de_respuesta)."""
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=request_headers, method="PATCH"
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")


def check_server_is_up():
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=5):
            return True
    except (urllib.error.URLError, ConnectionError):
        return False


def report(index, label, ok, detail=""):
    dots = "." * max(3, 42 - len(label))
    icon = "✅" if ok else "❌"
    line = f"[{index}/{TOTAL_CASES}] {label} {dots} {icon}"
    if detail:
        line += f" ({detail})"
    print(line)
    results.append((index, label, ok, detail))


class _ListLogHandler(logging.Handler):
    """Handler descartable para capturar logs de services.llm_connector durante un
    test puntual (casos 22/23), en vez de confiar en inspeccion visual de la consola."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))


# --- Caso 1: happy path ------------------------------------------------

def case_1_happy_path():
    payload = {
        "language": "Python",
        "exercise": "Crear una funcion que sume dos numeros.",
        "level": "Basico",
        "review_type": "Buenas practicas",
        "student_code": "def suma(a, b): return a + b",
    }
    status, body = post_json(REVIEW_URL, payload)
    if status != 200:
        report(1, "Caso feliz", False, f"esperado 200, recibido {status}: {body[:200]}")
        return None

    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        report(1, "Caso feliz", False, f"la respuesta no es JSON valido: {error}")
        return None

    missing_keys = SCHEMA_KEYS - data.keys()
    if missing_keys:
        report(1, "Caso feliz", False, f"faltan claves del schema: {missing_keys}")
        return None

    report(1, "Caso feliz", True, "200")
    return data


# --- Caso 2: campo faltante ---------------------------------------------

def case_2_missing_field():
    payload = {
        "language": "Python",
        "exercise": "Crear una funcion que sume dos numeros.",
        "level": "Basico",
        "review_type": "Buenas practicas",
        # falta student_code a proposito
    }
    status, body = post_json(REVIEW_URL, payload)
    ok = status == 400
    report(2, "Campo faltante", ok, f"{status}" if ok else f"esperado 400, recibido {status}: {body[:200]}")


# --- Caso 3: JSON malformado ---------------------------------------------

def case_3_malformed_json():
    broken_body = b'{"language": "Python", "exercise": "sin cerrar las comillas...'
    status, body = post(REVIEW_URL, broken_body)
    ok = status == 400
    report(3, "JSON malformado", ok, f"{status}" if ok else f"esperado 400, recibido {status}: {body[:200]}")


# --- Caso 4: codigo con error de sintaxis real ---------------------------

def case_4_syntax_error():
    payload = {
        "language": "Python",
        "exercise": "Crear una funcion que sume dos numeros.",
        "level": "Basico",
        "review_type": "Buenas practicas",
        "student_code": "def suma(a, b) return a+b",  # falta ':'
    }
    status, body = post_json(REVIEW_URL, payload)
    if status != 200:
        report(4, "Codigo con error de sintaxis", False, f"esperado 200, recibido {status}: {body[:200]}")
        return

    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        report(4, "Codigo con error de sintaxis", False, f"la respuesta no es JSON valido: {error}")
        return

    findings = data.get("findings", [])
    has_error_finding = any(f.get("category") == "Error" for f in findings)
    if not has_error_finding:
        categorias = [f.get("category") for f in findings]
        report(
            4, "Codigo con error de sintaxis", False,
            f"no se encontro ningun finding de categoria 'Error'; categorias recibidas: {categorias}",
        )
        return

    report(4, "Codigo con error de sintaxis", True, "200, error detectado")


# --- Caso 5: codigo vacio -------------------------------------------------
# Decision de diseño: un student_code vacio se trata como campo faltante.
# El Input Processor ya normaliza y descarta strings vacios/whitespace-only
# (ver services/llm_connector.py:_process_input, que usa .strip() antes de
# validar), asi que esto no requiere ningun cambio de pipeline: se comporta
# igual que el caso 2 y responde 400, no 200 con un finding artificial.

def case_5_empty_code():
    payload = {
        "language": "Python",
        "exercise": "Crear una funcion que sume dos numeros.",
        "level": "Basico",
        "review_type": "Buenas practicas",
        "student_code": "",
    }
    status, body = post_json(REVIEW_URL, payload)
    ok = status == 400
    report(5, "Codigo vacio", ok, f"{status}" if ok else f"esperado 400, recibido {status}: {body[:200]}")


# --- Caso 6: improved_code sin contaminacion de markdown ------------------

def case_6_no_markdown(happy_path_data):
    if happy_path_data is None:
        report(6, "Output sin markdown", False, "se salteo: el caso feliz (1) no devolvio datos")
        return

    improved_code = happy_path_data.get("suggested_code", {}).get("improved_code", "")
    problemas = []
    if "```" in improved_code:
        problemas.append("contiene ```")
    if improved_code.strip().lower().startswith("python"):
        problemas.append("empieza con 'python'")

    if problemas:
        report(6, "Output sin markdown", False, "; ".join(problemas))
        return

    report(6, "Output sin markdown", True)


# --- Caso 7: simulacion de 429 (mock, sin gastar cuota real) --------------

def case_7_quota_exceeded_mock():
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = genai_errors.APIError(
        429, {"error": {"message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"}}
    )

    with patch.object(llm_connector, "_get_client", return_value=fake_client):
        try:
            llm_connector.analizar_codigo(
                language="Python",
                exercise="Crear una funcion que sume dos numeros.",
                level="Basico",
                review_type="Buenas practicas",
                student_code="def suma(a, b): return a + b",
            )
        except llm_connector.QuotaExceededError:
            call_count = fake_client.models.generate_content.call_count
            if call_count != 1:
                report(
                    7, "Simulacion 429", False,
                    f"se esperaba 1 llamada sin reintento, hubo {call_count}",
                )
                return
            report(7, "Simulacion 429", True, "mensaje de cuota, sin reintento")
        except Exception as error:
            report(7, "Simulacion 429", False, f"excepcion inesperada: {type(error).__name__}: {error}")
        else:
            report(7, "Simulacion 429", False, "no se lanzo QuotaExceededError")


# --- Caso 8: GET /api/reviews/<id> devuelve la revision persistida -------
# Manda el session_id de la revision anonima del caso feliz: desde que GET /api/reviews/<id>
# aplica ownership (ver caso 17), leer una revision anonima sin el session_id correcto
# ahora da 403 en vez de 200 - este caso pasa a mandarlo, como haria cualquier caller real.

def case_8_get_review_by_id(happy_path_data):
    if happy_path_data is None:
        report(8, "GET revision por id", False, "se salteo: el caso feliz (1) no devolvio datos")
        return

    review_id = happy_path_data.get("review_id")
    session_id = happy_path_data.get("session_id")
    if not review_id:
        report(
            8, "GET revision por id", False,
            "el caso feliz no devolvio review_id (revisa el log del server: puede haber "
            "fallado la persistencia en Supabase, o falta correr migrations/001_init_supabase.sql)",
        )
        return

    status, body = get(
        f"{BASE_URL}/api/reviews/{urllib.parse.quote(str(review_id))}"
        f"?session_id={urllib.parse.quote(str(session_id))}"
    )
    if status != 200:
        report(8, "GET revision por id", False, f"esperado 200, recibido {status}: {body[:200]}")
        return

    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        report(8, "GET revision por id", False, f"la respuesta no es JSON valido: {error}")
        return

    if data.get("id") != review_id:
        report(8, "GET revision por id", False, f"id devuelto ({data.get('id')}) no coincide con review_id ({review_id})")
        return

    report(8, "GET revision por id", True, "200")


# --- Caso 9: GET /api/reviews?session_id=... incluye la revision recien creada --

def case_9_list_by_session(happy_path_data):
    if happy_path_data is None:
        report(9, "GET historial por sesion", False, "se salteo: el caso feliz (1) no devolvio datos")
        return

    session_id = happy_path_data.get("session_id")
    review_id = happy_path_data.get("review_id")
    if not session_id:
        report(9, "GET historial por sesion", False, "el caso feliz no devolvio session_id")
        return

    status, body = get(f"{BASE_URL}/api/reviews?session_id={urllib.parse.quote(str(session_id))}")
    if status != 200:
        report(9, "GET historial por sesion", False, f"esperado 200, recibido {status}: {body[:200]}")
        return

    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        report(9, "GET historial por sesion", False, f"la respuesta no es JSON valido: {error}")
        return

    if not isinstance(data, list):
        report(9, "GET historial por sesion", False, f"se esperaba una lista, se recibio: {type(data).__name__}")
        return

    ids = [row.get("id") for row in data]
    if review_id and review_id not in ids:
        report(9, "GET historial por sesion", False, f"review_id {review_id} no aparece en la lista de la sesion: {ids}")
        return

    report(9, "GET historial por sesion", True, f"{len(data)} revision(es)")


# --- Caso 10: JWT invalido en /api/review -> 401 --------------------------

def case_10_invalid_jwt():
    payload = {
        "language": "Python",
        "exercise": "Crear una funcion que sume dos numeros.",
        "level": "Basico",
        "review_type": "Buenas practicas",
        "student_code": "def suma(a, b): return a + b",
    }
    status, body = post_json(
        REVIEW_URL, payload, headers={"Authorization": "Bearer esto.no.es.un.jwt.valido"}
    )
    ok = status == 401
    report(10, "JWT invalido en /api/review", ok, f"{status}" if ok else f"esperado 401, recibido {status}: {body[:200]}")


# --- Caso 11: /api/reviews/mine sin token -> 401 --------------------------

def case_11_mine_without_token():
    status, body = get(f"{BASE_URL}/api/reviews/mine")
    ok = status == 401
    report(11, "GET /api/reviews/mine sin token", ok, f"{status}" if ok else f"esperado 401, recibido {status}: {body[:200]}")


# --- Caso 12 (opcional): JWT real persiste y recupera el student_id -------
# Ya no se puede "fabricar" un JWT valido firmando con un secreto conocido:
# el proyecto usa llaves asimetricas (ES256) y la llave privada solo la
# tiene Supabase. Se elige automatizar completo (en vez de pedir pegar un
# token a mano) porque no agrega mucha complejidad: se crea un usuario de
# prueba real via la Auth Admin API (con la service_role key, que si tiene
# permisos de admin), se loguea para obtener un access_token real firmado
# por Supabase, se usa igual que antes, y se borra el usuario al final.
# La fila en `students` la crea sola el trigger (nunca se inserta a mano,
# igual que en produccion) y se borra en cascada al eliminar el usuario.
#
# Importante: se usan clientes de Supabase nuevos y descartables, NO el
# singleton de services/supabase_client.py que usa la app real - se detecto
# que sign_in_with_password() muta el estado interno del cliente con el que
# se llama (deja de mandar la service_role key y pasa a mandar la sesion del
# usuario logueado). Si se reusara el cliente compartido de la app, esta
# prueba corromperia las credenciales de service_role del backend real para
# el resto del proceso.

def _get_supabase_admin_clients():
    """Dos clientes nuevos y descartables (admin + auth) para crear/loguear usuarios de prueba.

    Devuelve (None, None) si faltan las credenciales - el caller decide como reportarlo.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_role_key:
        return None, None
    return create_client(supabase_url, service_role_key), create_client(supabase_url, service_role_key)


def _create_and_sign_in_test_user(admin_client, auth_client):
    """Crea un usuario de prueba real via Auth Admin API y lo loguea. Devuelve (user_id, access_token)."""
    test_email = f"test-{uuid.uuid4()}@example.com"
    test_password = f"Test-{uuid.uuid4()}!"
    created = admin_client.auth.admin.create_user(
        {"email": test_email, "password": test_password, "email_confirm": True}
    )
    user_id = created.user.id
    session = auth_client.auth.sign_in_with_password({"email": test_email, "password": test_password})
    return user_id, session.session.access_token


def _cleanup_test_user(admin_client, user_id, case_number):
    try:
        admin_client.table("reviews").delete().eq("student_id", user_id).execute()
        admin_client.auth.admin.delete_user(user_id)
    except Exception as cleanup_error:
        print(f"  (aviso: no se pudo limpiar el usuario de prueba del caso {case_number}: {cleanup_error})")


def case_12_valid_jwt_persists_student_id():
    admin_client, auth_client = _get_supabase_admin_clients()
    if admin_client is None:
        report(12, "JWT real persiste student_id", False, "faltan SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY en .env")
        return

    user_id = None

    try:
        try:
            user_id, token = _create_and_sign_in_test_user(admin_client, auth_client)
        except Exception as error:
            report(12, "JWT real persiste student_id", False, f"no se pudo crear/loguear el usuario de prueba: {error}")
            return

        payload = {
            "language": "Python",
            "exercise": "Crear una funcion que sume dos numeros.",
            "level": "Basico",
            "review_type": "Buenas practicas",
            "student_code": "def suma(a, b): return a + b",
        }
        status, body = post_json(REVIEW_URL, payload, headers={"Authorization": f"Bearer {token}"})
        if status != 200:
            report(12, "JWT real persiste student_id", False, f"POST /api/review esperado 200, recibido {status}: {body[:200]}")
            return

        review_id = json.loads(body).get("review_id")
        if not review_id:
            report(12, "JWT real persiste student_id", False, "POST /api/review no devolvio review_id (¿fallo la persistencia?)")
            return

        status2, body2 = get(f"{BASE_URL}/api/reviews/mine", headers={"Authorization": f"Bearer {token}"})
        if status2 != 200:
            report(12, "JWT real persiste student_id", False, f"GET /api/reviews/mine esperado 200, recibido {status2}: {body2[:200]}")
            return

        rows = json.loads(body2)
        ids = [row.get("id") for row in rows]
        if review_id not in ids:
            report(12, "JWT real persiste student_id", False, f"review_id {review_id} no aparece en /api/reviews/mine: {ids}")
            return

        report(12, "JWT real persiste student_id", True, "200, usuario real, student_id persistido y recuperado")
    finally:
        if user_id:
            _cleanup_test_user(admin_client, user_id, 12)


# --- Caso 13: regenerar una revision anonima propia -----------------------

def case_13_regenerate_own_anonymous(happy_path_data):
    if happy_path_data is None:
        report(13, "Regenerar revision anonima propia", False, "se salteo: el caso feliz (1) no devolvio datos")
        return

    review_id = happy_path_data.get("review_id")
    session_id = happy_path_data.get("session_id")
    if not review_id or not session_id:
        report(13, "Regenerar revision anonima propia", False, "el caso feliz no devolvio review_id/session_id")
        return

    payload = {
        "session_id": session_id,
        "motivo_regeneracion": "Quiero una segunda opinion sobre el mismo codigo.",
    }
    status, body = post_json(f"{BASE_URL}/api/reviews/{review_id}/regenerate", payload)
    if status != 200:
        report(13, "Regenerar revision anonima propia", False, f"esperado 200, recibido {status}: {body[:200]}")
        return

    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        report(13, "Regenerar revision anonima propia", False, f"la respuesta no es JSON valido: {error}")
        return

    if data.get("parent_review_id") != review_id:
        report(
            13, "Regenerar revision anonima propia", False,
            f"parent_review_id ({data.get('parent_review_id')}) no coincide con la revision original ({review_id})",
        )
        return

    if not data.get("review_id"):
        report(
            13, "Regenerar revision anonima propia", False,
            "no se obtuvo review_id de la regeneracion (¿fallo la persistencia? revisa el log del server "
            "y confirma que corriste migrations/002_add_parent_review.sql)",
        )
        return

    missing_keys = SCHEMA_KEYS - data.keys()
    if missing_keys:
        report(13, "Regenerar revision anonima propia", False, f"faltan claves del schema: {missing_keys}")
        return

    report(13, "Regenerar revision anonima propia", True, "200, parent_review_id correcto")


# --- Caso 14: regenerar con un session_id que no es el dueno --------------

def case_14_regenerate_wrong_session(happy_path_data):
    if happy_path_data is None:
        report(14, "Regenerar con session_id ajeno", False, "se salteo: el caso feliz (1) no devolvio datos")
        return

    review_id = happy_path_data.get("review_id")
    if not review_id:
        report(14, "Regenerar con session_id ajeno", False, "el caso feliz no devolvio review_id")
        return

    payload = {"session_id": str(uuid.uuid4())}
    status, body = post_json(f"{BASE_URL}/api/reviews/{review_id}/regenerate", payload)
    ok = status == 403
    report(14, "Regenerar con session_id ajeno", ok, f"{status}" if ok else f"esperado 403, recibido {status}: {body[:200]}")


# --- Caso 15: regenerar un review_id inexistente --------------------------

def case_15_regenerate_nonexistent():
    fake_review_id = str(uuid.uuid4())
    status, body = post_json(f"{BASE_URL}/api/reviews/{fake_review_id}/regenerate", {"session_id": "cualquiera"})
    ok = status == 404
    report(15, "Regenerar revision inexistente", ok, f"{status}" if ok else f"esperado 404, recibido {status}: {body[:200]}")


# --- Caso 16: regenerar la revision de otro estudiante autenticado --------
# Reutiliza el helper de creacion de usuarios de prueba del caso 12. Cubre
# las dos variantes que menciona la tarea: sin mandar ningun JWT, y con el
# JWT de un usuario distinto al dueno - ambas deben dar 403.

def case_16_foreign_student_forbidden():
    admin_client, _ = _get_supabase_admin_clients()
    if admin_client is None:
        report(16, "Regenerar revision ajena", False, "faltan SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY en .env")
        return

    auth_client_owner = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    auth_client_other = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

    owner_id = None
    other_id = None

    try:
        try:
            owner_id, owner_token = _create_and_sign_in_test_user(admin_client, auth_client_owner)
            other_id, other_token = _create_and_sign_in_test_user(admin_client, auth_client_other)
        except Exception as error:
            report(16, "Regenerar revision ajena", False, f"no se pudieron crear los usuarios de prueba: {error}")
            return

        payload = {
            "language": "Python",
            "exercise": "Crear una funcion que sume dos numeros.",
            "level": "Basico",
            "review_type": "Buenas practicas",
            "student_code": "def suma(a, b): return a + b",
        }
        status, body = post_json(REVIEW_URL, payload, headers={"Authorization": f"Bearer {owner_token}"})
        if status != 200:
            report(16, "Regenerar revision ajena", False, f"POST /api/review (dueno) esperado 200, recibido {status}: {body[:200]}")
            return

        owner_review_id = json.loads(body).get("review_id")
        if not owner_review_id:
            report(16, "Regenerar revision ajena", False, "no se obtuvo review_id del dueno (¿fallo la persistencia?)")
            return

        regenerate_url = f"{BASE_URL}/api/reviews/{owner_review_id}/regenerate"
        status_no_token, body_no_token = post_json(regenerate_url, {})
        status_other, body_other = post_json(regenerate_url, {}, headers={"Authorization": f"Bearer {other_token}"})

        if status_no_token != 403:
            report(16, "Regenerar revision ajena", False, f"sin token esperado 403, recibido {status_no_token}: {body_no_token[:200]}")
            return
        if status_other != 403:
            report(16, "Regenerar revision ajena", False, f"con JWT de otro usuario esperado 403, recibido {status_other}: {body_other[:200]}")
            return

        report(16, "Regenerar revision ajena", True, "403 sin token y 403 con JWT ajeno")
    finally:
        for uid in (owner_id, other_id):
            if uid:
                _cleanup_test_user(admin_client, uid, 16)


# --- Caso 17: GET /api/reviews/<id> aplica ownership (hallazgo de la auditoria) ----
# Reproduce el exploit exacto que encontro docs/AUDITORIA_BACKEND.md: antes de esta
# tarea, este endpoint no llamaba a review_ownership.is_owner() en ningun punto y
# devolvia la fila completa (incluyendo student_code y student_id) a cualquiera con
# el UUID, sin token ni session_id.

def case_17_get_review_ownership_enforced():
    admin_client, auth_client = _get_supabase_admin_clients()
    if admin_client is None:
        report(17, "Ownership en GET /reviews/<id>", False, "faltan SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY en .env")
        return

    user_id = None

    try:
        try:
            user_id, token = _create_and_sign_in_test_user(admin_client, auth_client)
        except Exception as error:
            report(17, "Ownership en GET /reviews/<id>", False, f"no se pudo crear/loguear el usuario de prueba: {error}")
            return

        payload = {
            "language": "Python",
            "exercise": "Crear una funcion que sume dos numeros.",
            "level": "Basico",
            "review_type": "Buenas practicas",
            "student_code": "def suma(a, b): return a + b",
        }
        status, body = post_json(REVIEW_URL, payload, headers={"Authorization": f"Bearer {token}"})
        if status != 200:
            report(17, "Ownership en GET /reviews/<id>", False, f"POST /api/review esperado 200, recibido {status}: {body[:200]}")
            return

        review_id = json.loads(body).get("review_id")
        if not review_id:
            report(17, "Ownership en GET /reviews/<id>", False, "no se obtuvo review_id (¿fallo la persistencia?)")
            return

        get_url = f"{BASE_URL}/api/reviews/{review_id}"

        # El exploit original: leer sin token ni session_id.
        status_no_auth, body_no_auth = get(get_url)
        if status_no_auth != 403:
            report(
                17, "Ownership en GET /reviews/<id>", False,
                f"sin auth esperado 403, recibido {status_no_auth}: {body_no_auth[:200]}",
            )
            return

        # El dueno real si debe poder seguir leyendola.
        status_owner, body_owner = get(get_url, headers={"Authorization": f"Bearer {token}"})
        if status_owner != 200:
            report(
                17, "Ownership en GET /reviews/<id>", False,
                f"el dueno esperado 200, recibido {status_owner}: {body_owner[:200]}",
            )
            return

        report(17, "Ownership en GET /reviews/<id>", True, "403 sin auth, 200 para el dueno")
    finally:
        if user_id:
            _cleanup_test_user(admin_client, user_id, 17)


# --- Caso 18: excepcion no controlada devuelve JSON incluso con DEBUG=True --------
# Antes de esta tarea, con DEBUG=True (la config real del .env) un crash no anticipado
# devolvia el debugger interactivo de Werkzeug (HTML), no el JSON que definia
# @app.errorhandler(500) - ese handler nunca se ejecutaba en la practica. Usa la ruta
# interna /api/_internal/test-crash, que solo existe cuando DEBUG=True (ver app.py).

def case_18_unhandled_exception_returns_json():
    status, body = get(f"{BASE_URL}/api/_internal/test-crash")
    if status != 500:
        report(
            18, "Excepcion no controlada -> JSON", False,
            f"esperado 500, recibido {status}: {body[:200]}",
        )
        return

    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        report(
            18, "Excepcion no controlada -> JSON", False,
            f"el 500 no es JSON valido (¿sigue devolviendo HTML?): {error}. Body: {body[:200]}",
        )
        return

    if "error" not in data:
        report(18, "Excepcion no controlada -> JSON", False, f"falta la clave 'error' en el JSON: {data}")
        return

    report(18, "Excepcion no controlada -> JSON", True, "500 JSON, no HTML")


# --- Caso 19: body que excede MAX_CONTENT_LENGTH -> 413 JSON ----------------------

def case_19_body_too_large():
    huge_code = "x" * (200 * 1024)  # 200 KB, supera MAX_REQUEST_SIZE_BYTES (default 100 KB)
    payload = {
        "language": "Python",
        "exercise": "Test tamano de body",
        "level": "Basico",
        "review_type": "Buenas practicas",
        "student_code": huge_code,
    }
    status, body = post_json(REVIEW_URL, payload)
    if status != 413:
        report(19, "Body excede MAX_CONTENT_LENGTH", False, f"esperado 413, recibido {status}: {body[:200]}")
        return

    try:
        json.loads(body)
    except json.JSONDecodeError as error:
        report(
            19, "Body excede MAX_CONTENT_LENGTH", False,
            f"el 413 no es JSON valido: {error}. Body: {body[:200]}",
        )
        return

    report(19, "Body excede MAX_CONTENT_LENGTH", True, "413 JSON")


# --- Caso 20: student_code excede el limite de caracteres (sin exceder el body) ---
# Distinto del caso 19: este body es chico (bien por debajo de MAX_REQUEST_SIZE_BYTES),
# asi que el corte debe pasar en el Input Processor (400), no en el limite de tamano
# del request completo (413).

def case_20_student_code_char_limit():
    long_code = "x = 1\n" * 4000  # ~24000 caracteres, supera MAX_STUDENT_CODE_CHARS (default 20000)
    payload = {
        "language": "Python",
        "exercise": "Test limite de caracteres",
        "level": "Basico",
        "review_type": "Buenas practicas",
        "student_code": long_code,
    }
    status, body = post_json(REVIEW_URL, payload)
    ok = status == 400
    report(
        20, "student_code excede limite de caracteres", ok,
        f"{status}" if ok else f"esperado 400, recibido {status}: {body[:200]}",
    )


# --- Caso 21: rate limit propio del backend en /api/review -----------------------
# Debe ser el ULTIMO caso del script: agota deliberadamente el limite configurado
# (REVIEW_RATE_LIMIT, default 30 per minute) para /api/review, dejando ese endpoint
# rate-limited para el resto de la ventana de 1 minuto. Manda student_code vacio a
# proposito: la vista corta con 400 antes de llamar al LLM, pero el rate limiter ya
# cuenta el hit ANTES de que la vista se ejecute, asi que esto no gasta cuota real de
# Gemini. Las llamadas reales anteriores a /api/review (casos 1, 2, 3, 4, 5, 10, 12,
# 16, 19, 20) quedan repartidas a lo largo de varios minutos de wall-clock real (cada
# llamada al LLM tarda ~10-15s), asi que para cuando se llega aca ya salieron de la
# ventana de 1 minuto - este caso dispara, el solo, mas requests que el limite
# configurado (bien por encima de 30) en una rafaga de menos de un segundo, para
# garantizar el 429 sin depender de cuanto haya sobrevivido de los casos anteriores.

def case_21_rate_limit_backend():
    payload = {
        "language": "Python",
        "exercise": "Test rate limit",
        "level": "Basico",
        "review_type": "Buenas practicas",
        # student_code omitido a proposito: 400 rapido, sin gastar cuota del LLM.
    }
    statuses = []
    last_429_body = None
    for _ in range(40):
        status, body = post_json(REVIEW_URL, payload)
        statuses.append(status)
        if status == 429:
            last_429_body = body
            break

    if 429 not in statuses:
        report(
            21, "Rate limit propio del backend", False,
            f"no se alcanzo 429 tras {len(statuses)} requests seguidas; statuses: {statuses}",
        )
        return

    try:
        data = json.loads(last_429_body)
    except (json.JSONDecodeError, TypeError) as error:
        report(
            21, "Rate limit propio del backend", False,
            f"429 recibido pero la respuesta no es JSON valido: {error}",
        )
        return

    if "error" not in data:
        report(21, "Rate limit propio del backend", False, f"429 recibido pero sin clave 'error' en el JSON: {data}")
        return

    report(21, "Rate limit propio del backend", True, f"429 tras {len(statuses)} requests")


# --- Caso 22: Response Validator rechaza el primer intento, few-shot lo corrige --
# Igual que el caso 7, esto mockea services.llm_connector._get_client() y llama a
# analizar_codigo() DIRECTAMENTE (no via HTTP): mockear el cliente de Gemini del
# proceso vivo del servidor (otro proceso, arrancado con "python app.py") no es
# posible desde este script. El resultado sin excepcion es equivalente a lo que
# routes/review.py convierte en 200; ResponseValidationError es lo que convierte
# en 503 (ver routes/review.py:122 - no 502, ese codigo es solo para fallos de
# comunicacion con el LLM, no para fallos de formato del Response Schema).

def _valid_response_dict():
    return {
        "summary": {
            "language": "Python",
            "review_type": "Buenas practicas",
            "overall_assessment": "Analisis de prueba (caso 22/23).",
            "score": 80,
        },
        "findings": [],
        "explanation": [],
        "suggested_code": {"improved_code": "def f(): pass", "changes_summary": []},
        "tests": [],
        "warnings": [],
    }


def case_22_few_shot_retry_succeeds():
    invalid_json = json.dumps({"summary": {"language": "Python"}})  # a proposito: faltan claves requeridas
    valid_data = _valid_response_dict()
    valid_json = json.dumps(valid_data)

    fake_invalid_response = MagicMock()
    fake_invalid_response.text = invalid_json
    fake_valid_response = MagicMock()
    fake_valid_response.text = valid_json

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = [fake_invalid_response, fake_valid_response]

    log_handler = _ListLogHandler()
    llm_connector.logger.addHandler(log_handler)

    try:
        with patch.object(llm_connector, "_get_client", return_value=fake_client):
            try:
                result, prompt_sent = llm_connector.analizar_codigo(
                    language="Python",
                    exercise="Test few-shot (caso 22)",
                    level="Basico",
                    review_type="Buenas practicas",
                    student_code="def f(): pass",
                )
            except Exception as error:
                report(
                    22, "Few-shot corrige el formato (2do intento)", False,
                    f"excepcion inesperada: {type(error).__name__}: {error}",
                )
                return
    finally:
        llm_connector.logger.removeHandler(log_handler)

    if result != valid_data:
        report(
            22, "Few-shot corrige el formato (2do intento)", False,
            f"el resultado final no coincide con la respuesta valida esperada: {result}",
        )
        return

    call_count = fake_client.models.generate_content.call_count
    if call_count != 2:
        report(
            22, "Few-shot corrige el formato (2do intento)", False,
            f"se esperaban 2 llamadas al LLM (1 sin few-shot + 1 con few-shot), hubo {call_count}",
        )
        return

    call_args_list = fake_client.models.generate_content.call_args_list
    first_prompt = call_args_list[0].kwargs.get("contents", "")
    second_prompt = call_args_list[1].kwargs.get("contents", "")

    if "Ejemplo de referencia" in first_prompt:
        report(
            22, "Few-shot corrige el formato (2do intento)", False,
            "el PRIMER intento ya incluia Few-Shot Examples (no deberia, solo el segundo)",
        )
        return

    if "Ejemplo de referencia" not in second_prompt:
        report(
            22, "Few-shot corrige el formato (2do intento)", False,
            "el segundo intento no incluyo el bloque de Few-Shot Examples en el prompt",
        )
        return

    if "Ejemplo de referencia" not in prompt_sent:
        report(
            22, "Few-shot corrige el formato (2do intento)", False,
            "analizar_codigo() devolvio como prompt_sent el del primer intento (sin few-shot), "
            "no el del segundo intento (el que efectivamente produjo la respuesta valida)",
        )
        return

    log_text = "\n".join(log_handler.records)
    if "Few-Shot Examples" not in log_text:
        report(
            22, "Few-shot corrige el formato (2do intento)", False,
            f"no se encontro el log de activacion del camino few-shot; logs capturados: {log_handler.records}",
        )
        return

    report(22, "Few-shot corrige el formato (2do intento)", True, "resultado valido (equivalente a 200), log de few-shot presente")


# --- Caso 23: ambos intentos fallan la validacion -> sigue fallando como antes ----

def case_23_few_shot_retry_also_fails():
    # Mismo JSON invalido en los dos intentos - ni el original ni el "corregido con
    # few-shot" cumplen el schema.
    invalid_json = json.dumps({"summary": {"language": "Python"}})

    fake_response_1 = MagicMock()
    fake_response_1.text = invalid_json
    fake_response_2 = MagicMock()
    fake_response_2.text = invalid_json

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = [fake_response_1, fake_response_2]

    with patch.object(llm_connector, "_get_client", return_value=fake_client):
        try:
            llm_connector.analizar_codigo(
                language="Python",
                exercise="Test few-shot sin exito (caso 23)",
                level="Basico",
                review_type="Buenas practicas",
                student_code="def f(): pass",
            )
        except llm_connector.ResponseValidationError:
            pass
        except Exception as error:
            report(
                23, "Ambos intentos fallan -> error controlado", False,
                f"excepcion inesperada: {type(error).__name__}: {error}",
            )
            return
        else:
            report(23, "Ambos intentos fallan -> error controlado", False, "no se lanzo ResponseValidationError")
            return

    call_count = fake_client.models.generate_content.call_count
    if call_count != 2:
        report(
            23, "Ambos intentos fallan -> error controlado", False,
            f"se esperaban exactamente 2 llamadas al LLM (sin reintentar de mas), hubo {call_count}",
        )
        return

    report(
        23, "Ambos intentos fallan -> error controlado", True,
        "ResponseValidationError tras 2 intentos (equivalente al 503 real de routes/review.py, no 502)",
    )


# --- Caso 24: historial con una cadena de 3+ niveles de regeneracion -------------
# Cobertura identificada como faltante en la auditoria: list_review_history() se
# escribio para soportar profundidad arbitraria (sube hasta la raiz, despues baja
# por niveles) pero nunca se habia probado con mas de 2 niveles. Regenera dos veces
# seguidas (revision -> regeneracion 1 -> regeneracion 2) y confirma que /history
# devuelve las 3, en el mismo orden, sin importar desde cual de las 3 se consulte.

def case_24_history_three_levels():
    payload = {
        "language": "Python",
        "exercise": "Test historial de 3+ niveles",
        "level": "Basico",
        "review_type": "Buenas practicas",
        "student_code": "def suma(a, b): return a + b",
    }
    status, body = post_json(REVIEW_URL, payload)
    if status != 200:
        report(24, "Historial de 3+ niveles", False, f"POST /api/review esperado 200, recibido {status}: {body[:200]}")
        return

    data1 = json.loads(body)
    review_id_1 = data1.get("review_id")
    session_id = data1.get("session_id")
    if not review_id_1 or not session_id:
        report(24, "Historial de 3+ niveles", False, "la revision inicial no devolvio review_id/session_id")
        return

    status2, body2 = post_json(
        f"{BASE_URL}/api/reviews/{review_id_1}/regenerate",
        {"session_id": session_id, "motivo_regeneracion": "1ra regeneracion (caso 24)"},
    )
    if status2 != 200:
        report(24, "Historial de 3+ niveles", False, f"1ra regeneracion esperado 200, recibido {status2}: {body2[:200]}")
        return
    review_id_2 = json.loads(body2).get("review_id")
    if not review_id_2:
        report(24, "Historial de 3+ niveles", False, "la 1ra regeneracion no devolvio review_id (¿fallo la persistencia?)")
        return

    status3, body3 = post_json(
        f"{BASE_URL}/api/reviews/{review_id_2}/regenerate",
        {"session_id": session_id, "motivo_regeneracion": "2da regeneracion, sobre la 1ra (caso 24)"},
    )
    if status3 != 200:
        report(24, "Historial de 3+ niveles", False, f"2da regeneracion esperado 200, recibido {status3}: {body3[:200]}")
        return
    review_id_3 = json.loads(body3).get("review_id")
    if not review_id_3:
        report(24, "Historial de 3+ niveles", False, "la 2da regeneracion no devolvio review_id (¿fallo la persistencia?)")
        return

    expected_order = [review_id_1, review_id_2, review_id_3]
    expected_ids = set(expected_order)

    for query_id in expected_order:
        status_h, body_h = get(
            f"{BASE_URL}/api/reviews/{query_id}/history?session_id={urllib.parse.quote(session_id)}"
        )
        if status_h != 200:
            report(
                24, "Historial de 3+ niveles", False,
                f"GET history consultando desde {query_id} esperado 200, recibido {status_h}: {body_h[:200]}",
            )
            return

        try:
            chain = json.loads(body_h)
        except json.JSONDecodeError as error:
            report(24, "Historial de 3+ niveles", False, f"la respuesta no es JSON valido: {error}")
            return

        chain_ids = [row.get("id") for row in chain]
        if set(chain_ids) != expected_ids:
            report(
                24, "Historial de 3+ niveles", False,
                f"consultando desde {query_id}: se esperaban {expected_ids}, se obtuvo {set(chain_ids)}",
            )
            return
        if chain_ids != expected_order:
            report(
                24, "Historial de 3+ niveles", False,
                f"consultando desde {query_id}: orden incorrecto, se esperaba {expected_order}, se obtuvo {chain_ids}",
            )
            return

    report(24, "Historial de 3+ niveles", True, "3 niveles, mismo orden consultando desde cualquiera de los 3 ids")


# --- Caso 25: PATCH status "accepted" sobre una revision propia (anonima) --------

def case_25_patch_status_accepted():
    payload = {
        "language": "Python",
        "exercise": "Test PATCH status accepted",
        "level": "Basico",
        "review_type": "Buenas practicas",
        "student_code": "def suma(a, b): return a + b",
    }
    status, body = post_json(REVIEW_URL, payload)
    if status != 200:
        report(25, "PATCH status accepted (propia)", False, f"POST /api/review esperado 200, recibido {status}: {body[:200]}")
        return None

    data = json.loads(body)
    review_id = data.get("review_id")
    session_id = data.get("session_id")
    if not review_id or not session_id:
        report(25, "PATCH status accepted (propia)", False, "no se obtuvo review_id/session_id (¿fallo la persistencia?)")
        return None

    patch_status, patch_body = patch_json(
        f"{BASE_URL}/api/reviews/{review_id}", {"status": "accepted", "session_id": session_id}
    )
    if patch_status != 200:
        report(25, "PATCH status accepted (propia)", False, f"PATCH esperado 200, recibido {patch_status}: {patch_body[:200]}")
        return None

    patched = json.loads(patch_body)
    if patched.get("status") != "accepted":
        report(
            25, "PATCH status accepted (propia)", False,
            f"la respuesta del PATCH no refleja status='accepted': {patched.get('status')}",
        )
        return None

    get_status, get_body = get(f"{BASE_URL}/api/reviews/{review_id}?session_id={urllib.parse.quote(session_id)}")
    if get_status != 200:
        report(25, "PATCH status accepted (propia)", False, f"GET posterior esperado 200, recibido {get_status}: {get_body[:200]}")
        return None

    refetched = json.loads(get_body)
    if refetched.get("status") != "accepted":
        report(25, "PATCH status accepted (propia)", False, f"status no quedo guardado: {refetched.get('status')}")
        return None

    report(25, "PATCH status accepted (propia)", True, "200, status='accepted' persistido")
    return {"review_id": review_id, "session_id": session_id}


# --- Caso 26: PATCH solo student_comment no pisa el status anterior --------------

def case_26_patch_comment_keeps_status(case_25_data):
    if case_25_data is None:
        report(26, "PATCH solo student_comment", False, "se salteo: el caso 25 no devolvio datos")
        return

    review_id = case_25_data["review_id"]
    session_id = case_25_data["session_id"]
    comment = "Buena explicacion, pero ya lo habia corregido asi."

    patch_status, patch_body = patch_json(
        f"{BASE_URL}/api/reviews/{review_id}",
        {"student_comment": comment, "session_id": session_id},
    )
    if patch_status != 200:
        report(26, "PATCH solo student_comment", False, f"esperado 200, recibido {patch_status}: {patch_body[:200]}")
        return

    patched = json.loads(patch_body)
    if patched.get("student_comment") != comment:
        report(26, "PATCH solo student_comment", False, f"student_comment no coincide: {patched.get('student_comment')}")
        return

    if patched.get("status") != "accepted":
        report(
            26, "PATCH solo student_comment", False,
            f"el status se piso sin querer (deberia seguir 'accepted' del caso 25): {patched.get('status')}",
        )
        return

    report(26, "PATCH solo student_comment", True, "200, comentario guardado y status previo intacto")


# --- Caso 27: PATCH sobre una revision ajena -------------------------------------
# Mismo criterio de ownership que el caso 17 (GET), reutilizando los helpers de
# usuario de prueba de los casos 12/16/17.

def case_27_patch_foreign_review_forbidden():
    admin_client, auth_client = _get_supabase_admin_clients()
    if admin_client is None:
        report(27, "PATCH revision ajena", False, "faltan SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY en .env")
        return

    user_id = None
    try:
        try:
            user_id, token = _create_and_sign_in_test_user(admin_client, auth_client)
        except Exception as error:
            report(27, "PATCH revision ajena", False, f"no se pudo crear/loguear el usuario de prueba: {error}")
            return

        payload = {
            "language": "Python",
            "exercise": "Test PATCH revision ajena",
            "level": "Basico",
            "review_type": "Buenas practicas",
            "student_code": "def suma(a, b): return a + b",
        }
        status, body = post_json(REVIEW_URL, payload, headers={"Authorization": f"Bearer {token}"})
        if status != 200:
            report(27, "PATCH revision ajena", False, f"POST /api/review (dueno) esperado 200, recibido {status}: {body[:200]}")
            return

        owner_review_id = json.loads(body).get("review_id")
        if not owner_review_id:
            report(27, "PATCH revision ajena", False, "no se obtuvo review_id del dueno (¿fallo la persistencia?)")
            return

        patch_status, patch_body = patch_json(f"{BASE_URL}/api/reviews/{owner_review_id}", {"status": "discarded"})
        if patch_status != 403:
            report(27, "PATCH revision ajena", False, f"esperado 403, recibido {patch_status}: {patch_body[:200]}")
            return

        report(27, "PATCH revision ajena", True, "403 sin autenticacion ni session_id")
    finally:
        if user_id:
            _cleanup_test_user(admin_client, user_id, 27)


# --- Caso 28: review_type fuera de la lista controlada -> 400 -------------------

def case_28_invalid_review_type():
    payload = {
        "language": "Python",
        "exercise": "Test review_type invalido",
        "level": "Basico",
        "review_type": "cositas raras",
        "student_code": "def suma(a, b): return a + b",
    }
    status, body = post_json(REVIEW_URL, payload)
    if status != 400:
        report(28, "review_type invalido", False, f"esperado 400, recibido {status}: {body[:200]}")
        return

    data = json.loads(body)
    error_message = data.get("error", "")
    if "cositas raras" not in error_message:
        report(28, "review_type invalido", False, f"el mensaje no menciona el valor invalido recibido: {error_message}")
        return

    missing_allowed_values = [value for value in llm_connector.ALLOWED_REVIEW_TYPES if value not in error_message]
    if missing_allowed_values:
        report(
            28, "review_type invalido", False,
            f"el mensaje no incluye todos los valores permitidos, faltan: {missing_allowed_values}",
        )
        return

    report(28, "review_type invalido", True, "400, mensaje incluye los valores permitidos")


# --- Caso 29: GET /api/dashboard/metrics tiene la forma esperada -----------------

def case_29_dashboard_metrics_shape():
    status, body = get(f"{BASE_URL}/api/dashboard/metrics")
    if status != 200:
        report(29, "GET /api/dashboard/metrics", False, f"esperado 200, recibido {status}: {body[:200]}")
        return

    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        report(29, "GET /api/dashboard/metrics", False, f"la respuesta no es JSON valido: {error}")
        return

    expected_keys = {
        "total_reviews", "reviews_by_language", "reviews_by_status",
        "regenerated_count", "most_frequent_findings",
    }
    missing_keys = expected_keys - data.keys()
    if missing_keys:
        report(29, "GET /api/dashboard/metrics", False, f"faltan claves: {missing_keys}")
        return

    # No se compara contra un conteo exacto de "revisiones creadas por esta corrida":
    # varios casos (12, 16, 17, 27) borran su propia revision de prueba al limpiar el
    # usuario de Supabase Auth que crearon (ver _cleanup_test_user), asi que un
    # conteo exacto de "lo que deberia quedar" no reflejaria la tabla real. Se valida
    # coherencia (tipos correctos, no negativos) y un piso conservador basado en las
    # revisiones que sabemos que NO se borran (la del caso feliz y la del caso 25).
    if not isinstance(data["total_reviews"], int) or data["total_reviews"] < 0:
        report(29, "GET /api/dashboard/metrics", False, f"total_reviews invalido: {data['total_reviews']}")
        return

    if not isinstance(data["reviews_by_language"], dict):
        report(29, "GET /api/dashboard/metrics", False, f"reviews_by_language deberia ser un objeto: {data['reviews_by_language']}")
        return

    if not isinstance(data["reviews_by_status"], dict):
        report(29, "GET /api/dashboard/metrics", False, f"reviews_by_status deberia ser un objeto: {data['reviews_by_status']}")
        return

    if not isinstance(data["regenerated_count"], int) or data["regenerated_count"] < 0:
        report(29, "GET /api/dashboard/metrics", False, f"regenerated_count invalido: {data['regenerated_count']}")
        return

    if not isinstance(data["most_frequent_findings"], list):
        report(29, "GET /api/dashboard/metrics", False, f"most_frequent_findings deberia ser una lista: {data['most_frequent_findings']}")
        return

    for item in data["most_frequent_findings"]:
        if not (isinstance(item, dict) and isinstance(item.get("title"), str) and isinstance(item.get("count"), int)):
            report(29, "GET /api/dashboard/metrics", False, f"item invalido en most_frequent_findings: {item}")
            return

    if data["total_reviews"] < 1:
        report(
            29, "GET /api/dashboard/metrics", False,
            "total_reviews deberia ser al menos 1 (esta misma corrida ya creo revisiones que no se borran)",
        )
        return

    report(29, "GET /api/dashboard/metrics", True, f"200, total_reviews={data['total_reviews']}")


# --- Caso 30: el dashboard refleja el status "accepted" del caso 25 --------------

def case_30_dashboard_reflects_accepted_status():
    status, body = get(f"{BASE_URL}/api/dashboard/metrics")
    if status != 200:
        report(30, "Dashboard refleja status accepted", False, f"esperado 200, recibido {status}: {body[:200]}")
        return

    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        report(30, "Dashboard refleja status accepted", False, f"la respuesta no es JSON valido: {error}")
        return

    reviews_by_status = data.get("reviews_by_status", {})
    accepted_count = reviews_by_status.get("accepted", 0)
    if not isinstance(accepted_count, int) or accepted_count <= 0:
        report(
            30, "Dashboard refleja status accepted", False,
            f"se esperaba reviews_by_status['accepted'] > 0 (el caso 25 ya acepto una revision), "
            f"se obtuvo: {reviews_by_status}",
        )
        return

    report(30, "Dashboard refleja status accepted", True, f"accepted={accepted_count}")


# --- Caso 31: GET /api/dashboard/mine filtra por estudiante -----------------
# A diferencia de GET /api/dashboard/metrics (publico, agrega TODO el sistema),
# este endpoint exige auth y solo agrega las revisiones del student_id del JWT.

def case_31_dashboard_mine_filters_by_student():
    admin_client, _ = _get_supabase_admin_clients()
    if admin_client is None:
        report(31, "GET /api/dashboard/mine filtra por estudiante", False, "faltan SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY en .env")
        return

    auth_client_a = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    auth_client_b = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

    user_a_id = None
    user_b_id = None

    try:
        try:
            user_a_id, token_a = _create_and_sign_in_test_user(admin_client, auth_client_a)
            user_b_id, token_b = _create_and_sign_in_test_user(admin_client, auth_client_b)
        except Exception as error:
            report(31, "GET /api/dashboard/mine filtra por estudiante", False, f"no se pudieron crear los usuarios de prueba: {error}")
            return

        # Usuario B, sin ninguna revision propia todavia: debe ver las 5 metricas en
        # cero, no un error.
        status_b, body_b = get(f"{BASE_URL}/api/dashboard/mine", headers={"Authorization": f"Bearer {token_b}"})
        if status_b != 200:
            report(31, "GET /api/dashboard/mine filtra por estudiante", False, f"usuario sin revisiones esperado 200, recibido {status_b}: {body_b[:200]}")
            return
        data_b = json.loads(body_b)
        if data_b.get("total_reviews") != 0:
            report(31, "GET /api/dashboard/mine filtra por estudiante", False, f"usuario sin revisiones deberia ver total_reviews=0, se obtuvo: {data_b.get('total_reviews')}")
            return

        # Usuario A crea una revision propia (lenguaje distintivo para poder verificarla).
        payload = {
            "language": "Kotlin",
            "exercise": "Test de GET /api/dashboard/mine",
            "level": "Basico",
            "review_type": "Buenas practicas",
            "student_code": "fun suma(a: Int, b: Int): Int { return a + b }",
        }
        status_review, body_review = post_json(REVIEW_URL, payload, headers={"Authorization": f"Bearer {token_a}"})
        if status_review != 200:
            report(31, "GET /api/dashboard/mine filtra por estudiante", False, f"POST /api/review (usuario A) esperado 200, recibido {status_review}: {body_review[:200]}")
            return

        # /api/dashboard/mine del usuario A debe reflejar esa revision.
        status_a, body_a = get(f"{BASE_URL}/api/dashboard/mine", headers={"Authorization": f"Bearer {token_a}"})
        if status_a != 200:
            report(31, "GET /api/dashboard/mine filtra por estudiante", False, f"usuario A esperado 200, recibido {status_a}: {body_a[:200]}")
            return
        data_a = json.loads(body_a)
        if data_a.get("total_reviews", 0) < 1 or data_a.get("reviews_by_language", {}).get("Kotlin", 0) < 1:
            report(31, "GET /api/dashboard/mine filtra por estudiante", False, f"usuario A deberia ver su propia revision de Kotlin, se obtuvo: {data_a}")
            return

        # El usuario B sigue en 0 despues de que A creo la suya - no se mezclan.
        status_b2, body_b2 = get(f"{BASE_URL}/api/dashboard/mine", headers={"Authorization": f"Bearer {token_b}"})
        if status_b2 != 200:
            report(31, "GET /api/dashboard/mine filtra por estudiante", False, f"usuario B (2da consulta) esperado 200, recibido {status_b2}: {body_b2[:200]}")
            return
        data_b2 = json.loads(body_b2)
        if data_b2.get("total_reviews") != 0:
            report(31, "GET /api/dashboard/mine filtra por estudiante", False, f"usuario B deberia seguir en 0 tras la revision de A, se obtuvo: {data_b2.get('total_reviews')}")
            return

        # Sin token -> 401 (auth obligatoria, a diferencia del dashboard global).
        status_401, body_401 = get(f"{BASE_URL}/api/dashboard/mine")
        if status_401 != 401:
            report(31, "GET /api/dashboard/mine filtra por estudiante", False, f"sin token esperado 401, recibido {status_401}: {body_401[:200]}")
            return

        report(31, "GET /api/dashboard/mine filtra por estudiante", True, "200 filtrado por usuario (0 sin revisiones, refleja las propias), 401 sin token")
    finally:
        for uid in (user_a_id, user_b_id):
            if uid:
                _cleanup_test_user(admin_client, uid, 31)


def main():
    print(f"Verificando servidor en {BASE_URL} ...")
    if not check_server_is_up():
        print(f"No se pudo conectar con {BASE_URL}.")
        print("Asegurate de correr 'python app.py' en otra terminal antes de este script.")
        sys.exit(1)

    happy_path_data = case_1_happy_path()
    case_2_missing_field()
    case_3_malformed_json()
    case_4_syntax_error()
    case_5_empty_code()
    case_6_no_markdown(happy_path_data)
    case_7_quota_exceeded_mock()
    case_8_get_review_by_id(happy_path_data)
    case_9_list_by_session(happy_path_data)
    case_10_invalid_jwt()
    case_11_mine_without_token()
    case_12_valid_jwt_persists_student_id()
    case_13_regenerate_own_anonymous(happy_path_data)
    case_14_regenerate_wrong_session(happy_path_data)
    case_15_regenerate_nonexistent()
    case_16_foreign_student_forbidden()
    case_17_get_review_ownership_enforced()
    case_18_unhandled_exception_returns_json()
    case_19_body_too_large()
    case_20_student_code_char_limit()
    # case_24, case_25/26/27/28 (aunque sus numeros son mas altos) corren ANTES que
    # case_21 a proposito: case_21 agota el rate limit de /api/review para el resto
    # de la ventana de 1 minuto, y todos estos todavia necesitan hacer llamadas
    # reales a /api/review. case_21 sigue siendo el ultimo caso que golpea el
    # servidor real.
    case_24_history_three_levels()
    case_25_data = case_25_patch_status_accepted()
    case_26_patch_comment_keeps_status(case_25_data)
    case_27_patch_foreign_review_forbidden()
    case_28_invalid_review_type()
    case_29_dashboard_metrics_shape()
    case_30_dashboard_reflects_accepted_status()
    case_31_dashboard_mine_filters_by_student()
    case_21_rate_limit_backend()
    case_22_few_shot_retry_succeeds()
    case_23_few_shot_retry_also_fails()

    ok_count = sum(1 for _, _, ok, _ in results if ok)
    print()
    print(f"Resumen: {ok_count}/{TOTAL_CASES} casos OK")

    if ok_count != TOTAL_CASES:
        print("\nDetalle de casos fallidos:")
        for index, label, ok, detail in results:
            if not ok:
                print(f"  - [{index}] {label}: {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
