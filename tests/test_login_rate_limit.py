"""HU-31 / R-10: límite de intentos de `POST /auth/login` (integración)."""

import logging

import pytest

from app.config import settings
from app.core.exceptions import ErrorResponse
from app.models.model_user import Role

EMAIL = "ana@test.com"
PASSWORD = "secreto123"
WINDOW_SECONDS = settings.LOGIN_WINDOW_MINUTES * 60
MAX_ATTEMPTS = settings.LOGIN_MAX_ATTEMPTS


def login(client, email=EMAIL, password=PASSWORD, headers=None):
    return client.post(
        "/auth/login", data={"username": email, "password": password}, headers=headers
    )


def fail(client, times, email=EMAIL, headers=None):
    for _ in range(times):
        assert login(client, email, "incorrecta", headers).status_code == 401


@pytest.fixture
def ana(make_user):
    return make_user(Role.customer, email=EMAIL)


@pytest.fixture
def ip_header(monkeypatch):
    monkeypatch.setattr(settings, "CLIENT_IP_HEADER", "True-Client-IP")
    return "True-Client-IP"


def test_cinco_fallos_dan_401_y_el_sexto_429(client, ana):
    fail(client, MAX_ATTEMPTS)

    response = login(client, password="incorrecta")

    assert response.status_code == 429
    body = ErrorResponse.model_validate(response.json())
    assert body.code == "too_many_attempts"
    assert body.detail == "Too many failed login attempts. Try again later."
    assert 1 <= int(response.headers["Retry-After"]) <= WINDOW_SECONDS


def test_durante_el_bloqueo_la_contrasena_correcta_tambien_da_429(client, ana):
    fail(client, MAX_ATTEMPTS)

    assert login(client).status_code == 429


def test_un_login_correcto_borra_los_fallos(client, ana):
    fail(client, MAX_ATTEMPTS - 1)
    assert login(client).status_code == 200

    fail(client, MAX_ATTEMPTS)

    assert login(client).status_code == 429


def test_otro_email_desde_la_misma_ip_no_esta_bloqueado(client, ana, make_user):
    make_user(Role.waiter, email="otra@test.com")
    fail(client, MAX_ATTEMPTS)

    assert login(client, email="otra@test.com").status_code == 200


def test_el_mismo_email_desde_otra_ip_no_esta_bloqueado(client, ana, ip_header):
    fail(client, MAX_ATTEMPTS, headers={ip_header: "203.0.113.7"})

    assert login(client, headers={ip_header: "203.0.113.7"}).status_code == 429
    assert login(client, headers={ip_header: "198.51.100.1"}).status_code == 200


def test_x_forwarded_for_no_cambia_la_ip(client, ana, ip_header):
    fail(client, MAX_ATTEMPTS, headers={ip_header: "203.0.113.7"})

    response = login(
        client, headers={ip_header: "203.0.113.7", "X-Forwarded-For": "198.51.100.1"}
    )

    assert response.status_code == 429


def test_sin_cabecera_configurada_se_ignoran_las_cabeceras_del_cliente(client, ana):
    fail(client, MAX_ATTEMPTS, headers={"True-Client-IP": "203.0.113.7"})

    assert login(client, headers={"True-Client-IP": "198.51.100.1"}).status_code == 429


def test_el_email_cuenta_igual_en_mayusculas_y_con_espacios(client, ana):
    fail(client, 3, email="  Ana@TEST.com ")
    fail(client, MAX_ATTEMPTS - 3)

    assert login(client).status_code == 429


def test_cuenta_un_email_que_no_existe(client):
    fail(client, MAX_ATTEMPTS, email="nadie@test.com")

    assert login(client, email="nadie@test.com").status_code == 429


def test_cuenta_un_usuario_desactivado(client, make_user):
    make_user(Role.customer, email=EMAIL, is_active=False)
    for _ in range(MAX_ATTEMPTS):
        assert login(client).status_code == 401

    assert login(client).status_code == 429


def test_un_422_no_cuenta(client, ana):
    for _ in range(MAX_ATTEMPTS + 2):
        response = client.post("/auth/login", data={"username": EMAIL})
        assert response.status_code == 422

    assert login(client).status_code == 200


def test_avisa_en_el_log_al_bloquear_sin_la_contrasena(client, ana, caplog):
    with caplog.at_level(logging.WARNING, logger="app.services.login_rate_limit_service"):
        fail(client, MAX_ATTEMPTS)

    blocked = [r for r in caplog.records if r.getMessage() == "Login blocked"]
    assert len(blocked) == 1
    assert blocked[0].client_ip == "testclient"
    assert blocked[0].email == EMAIL
    assert "incorrecta" not in caplog.text


def test_swagger_documenta_el_429_del_login(client):
    responses = client.get("/openapi.json").json()["paths"]["/auth/login"]["post"]["responses"]

    error = responses["429"]
    assert error["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")
    assert "too_many_attempts" in error["description"]
    assert "Retry-After" in error["description"]
