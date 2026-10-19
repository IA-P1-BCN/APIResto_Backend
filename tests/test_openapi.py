"""Contrato de Swagger para `/auth` y `/users` (HU-26).

Recorre el `/openapi.json` real, así que un endpoint nuevo de `/auth` o `/users` tiene que
llegar documentado: tags, summary, descripción con el rol, errores con el formato común,
parámetros descritos y cuerpos JSON con ejemplo.
"""

import pytest
from fastapi import APIRouter, FastAPI

from app.main import app

DOCUMENTED_PREFIXES = ("/auth", "/users")
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
EXPECTED_OPERATIONS = {
    ("post", "/auth/register"),
    ("post", "/auth/login"),
    ("post", "/auth/social/{provider}"),
    ("get", "/auth/me"),
    ("post", "/auth/set-password"),
    ("post", "/auth/refresh"),
    ("post", "/auth/logout"),
    ("post", "/users/"),
    ("get", "/users/"),
    ("get", "/users/{user_id}"),
    ("put", "/users/{user_id}"),
    ("patch", "/users/{user_id}/deactivate"),
    ("delete", "/users/{user_id}"),
    ("post", "/users/{user_id}/restore"),
    ("post", "/users/invite"),
    ("patch", "/users/me"),
    ("post", "/users/me/password"),
}


def _operations(spec: dict) -> list[tuple[str, str, dict]]:
    return [
        (method, path, operation)
        for path, operations in spec["paths"].items()
        if path.startswith(DOCUMENTED_PREFIXES)
        for method, operation in operations.items()
        if method in HTTP_METHODS
    ]


def _json_schema(content: dict) -> dict:
    return content.get("application/json", {}).get("schema", {})


def _ref_name(schema: dict) -> str:
    return schema.get("$ref", "").rsplit("/", 1)[-1]


def documentation_problems(spec: dict, path: str, operation: dict) -> list[str]:
    """Lista lo que le falta a un endpoint para cumplir la spec de HU-26 (vacía = completo)."""
    problems = [f"falta {field}" for field in ("tags", "summary", "description") if not operation.get(field)]
    if "Rol:" not in operation.get("description", ""):
        problems.append("la descripción no indica el rol (`Rol: ...`)")

    responses = operation["responses"]
    if "security" in operation:
        if "401" not in responses:
            problems.append("endpoint protegido sin 401")
        is_admin_only = path.startswith("/users") and not path.startswith("/users/me")
        if is_admin_only and "403" not in responses:
            problems.append("endpoint de admin sin 403")

    for code, response in responses.items():
        if code[0] not in "45":
            continue
        expected = "ValidationErrorResponse" if code == "422" else "ErrorResponse"
        found = _ref_name(_json_schema(response.get("content", {})))
        if found != expected:
            problems.append(f"{code} documentado con {found or 'nada'} en vez de {expected}")

    for parameter in operation.get("parameters", []):
        if not parameter.get("description"):
            problems.append(f"parámetro `{parameter['name']}` sin descripción")

    body = _json_schema(operation.get("requestBody", {}).get("content", {}))
    if body:
        schema = spec["components"]["schemas"].get(_ref_name(body), body)
        if "examples" not in schema:
            problems.append("cuerpo JSON sin ejemplo")
    return problems


SPEC = app.openapi()
OPERATIONS = _operations(SPEC)


def test_estan_todos_los_endpoints_de_auth_y_users():
    assert EXPECTED_OPERATIONS <= {(method, path) for method, path, _ in OPERATIONS}


@pytest.mark.parametrize(
    ("method", "path", "operation"),
    OPERATIONS,
    ids=[f"{method.upper()} {path}" for method, path, _ in OPERATIONS],
)
def test_endpoint_documentado(method, path, operation):
    assert documentation_problems(SPEC, path, operation) == []


@pytest.mark.parametrize("path", ["/auth/login", "/auth/social/{provider}"])
def test_login_documenta_token_out(path):
    response = SPEC["paths"][path]["post"]["responses"]["200"]

    assert _ref_name(_json_schema(response["content"])) == "TokenOut"


def test_authorize_usa_oauth2_password_con_auth_login():
    schemes = SPEC["components"]["securitySchemes"]

    assert schemes["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"] == "/auth/login"


def test_detecta_un_endpoint_sin_documentar():
    router = APIRouter(prefix="/auth")

    @router.get("/sin-documentar")
    def undocumented(q: int):
        return {}

    probe = FastAPI()
    probe.include_router(router)
    spec = probe.openapi()
    [(_, path, operation)] = _operations(spec)

    problems = documentation_problems(spec, path, operation)

    assert "falta tags" in problems
    assert "falta description" in problems
    assert "parámetro `q` sin descripción" in problems
    assert "422 documentado con HTTPValidationError en vez de ValidationErrorResponse" in problems
