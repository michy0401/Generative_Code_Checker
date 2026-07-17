"""
Script standalone de pruebas manuales contra el servidor real.

Uso:
    1. En una terminal: python app.py
    2. En otra terminal: python tests/test_api_manual.py

No es un test de pytest: es un vistazo rapido de 21 casos mientras se
desarrolla, pensado para correrse a mano contra el servidor local.
"""

import json
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

TOTAL_CASES = 21
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
    case_21_rate_limit_backend()

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
