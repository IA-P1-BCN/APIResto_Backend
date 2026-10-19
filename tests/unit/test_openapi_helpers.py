"""Helpers de documentación Swagger (HU-26)."""

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import ErrorResponse
from app.core.openapi import ValidationErrorResponse, error_responses
from app.main import app


def test_error_responses_usa_error_response_y_descripcion_por_defecto():
    responses = error_responses(401, 404)

    assert set(responses) == {401, 404}
    assert responses[401]["model"] is ErrorResponse
    assert responses[404]["description"] == "El recurso no existe."


def test_error_responses_documenta_el_422_con_la_lista_de_errores():
    responses = error_responses(422)

    assert responses[422]["model"] is ValidationErrorResponse
    assert "errors" in ValidationErrorResponse.model_fields


def test_error_responses_acepta_descripcion_propia():
    responses = error_responses(409, descriptions={409: "Email duplicado (`conflict`)."})

    assert responses[409]["description"] == "Email duplicado (`conflict`)."


def test_error_responses_rechaza_un_codigo_sin_descripcion():
    with pytest.raises(ValueError):
        error_responses(418)


def test_422_real_coincide_con_validation_error_response():
    client = TestClient(app)

    body = client.post("/auth/register", json={}).json()

    parsed = ValidationErrorResponse.model_validate(body)
    assert parsed.code == "validation_error"
    assert parsed.errors


def test_422_de_negocio_sin_errors_tambien_coincide_con_el_modelo():
    client = TestClient(app)

    body = client.post(
        "/auth/social/google",
        json={"code": "x", "redirect_uri": "https://no-permitido.example.com/cb"},
    ).json()

    parsed = ValidationErrorResponse.model_validate(body)
    assert parsed.code == "redirect_uri_not_allowed"
    assert parsed.errors is None


def test_openapi_incluye_descripcion_general_y_tags_con_descripcion():
    spec = TestClient(app).get("/openapi.json").json()

    assert "Cómo autenticarse" in spec["info"]["description"]
    tags = {tag["name"]: tag.get("description") for tag in spec["tags"]}
    assert tags["auth"]
    assert tags["users"]
