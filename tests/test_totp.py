import logging
import re
from datetime import UTC, datetime, timedelta

import jwt
import pyotp
import pytest

from app.config import settings
from app.models.model_user import Role, User
from app.routers import auth as auth_router
from app.services import totp_service
from tests.conftest import TestingSessionLocal


def _login(client, email="waiter@test.com", password="secreto123"):
    return client.post("/auth/login", data={"username": email, "password": password})


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def waiter(make_user):
    return make_user(Role.waiter)


@pytest.fixture
def headers(client, waiter):
    return _headers(_login(client).json()["access_token"])


@pytest.fixture
def enabled(client, headers):
    """Activa la 2FA del camarero y devuelve el secreto y los códigos de recuperación."""
    secret = client.post("/users/me/2fa/setup", headers=headers).json()["secret"]
    codes = client.post(
        "/users/me/2fa/enable", headers=headers, json={"code": pyotp.TOTP(secret).now()}
    ).json()["recovery_codes"]
    return secret, codes


def _wrong_code(secret):
    """Un código de 6 dígitos que no es válido ahora (ni en la ventana de ±30 s)."""
    totp = pyotp.TOTP(secret)
    now = datetime.now(UTC)
    valid = {totp.at(now + timedelta(seconds=s)) for s in (-30, 0, 30)}
    return next(c for c in (f"{n:06d}" for n in range(1000)) if c not in valid)


def _fresh(db, user):
    db.expire_all()
    return db.get(User, user.id)


def _verify(client, mfa_token, code):
    return client.post("/auth/2fa/verify", json={"mfa_token": mfa_token, "code": code})


def test_status_sin_2fa(client, headers):
    r = client.get("/users/me/2fa", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"enabled": False, "recovery_codes_left": 0}


def test_setup_devuelve_secreto_uri_y_qr(client, headers):
    r = client.post("/users/me/2fa/setup", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["otpauth_uri"].startswith("otpauth://totp/APIResto:waiter%40test.com?")
    assert f"secret={body['secret']}" in body["otpauth_uri"]
    assert body["qr_svg"].startswith("<svg")
    assert 'xmlns="http://www.w3.org/2000/svg"' in body["qr_svg"]


def test_activar_con_codigo_valido(client, headers, enabled):
    _, codes = enabled
    assert len(codes) == 8
    assert len(set(codes)) == 8
    assert client.get("/users/me/2fa", headers=headers).json() == {"enabled": True, "recovery_codes_left": 8}


def test_activar_con_codigo_malo(client, headers):
    secret = client.post("/users/me/2fa/setup", headers=headers).json()["secret"]
    r = client.post("/users/me/2fa/enable", headers=headers, json={"code": _wrong_code(secret)})
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_totp_code"


def test_activar_sin_setup(client, headers):
    r = client.post("/users/me/2fa/enable", headers=headers, json={"code": "123456"})
    assert r.status_code == 409
    assert r.json()["code"] == "totp_not_set_up"


def test_setup_y_enable_con_2fa_activa(client, headers, enabled):
    r = client.post("/users/me/2fa/setup", headers=headers)
    assert r.status_code == 409
    assert r.json()["code"] == "totp_already_enabled"
    r = client.post("/users/me/2fa/enable", headers=headers, json={"code": "123456"})
    assert r.status_code == 409
    assert r.json()["code"] == "totp_already_enabled"


def test_gestion_requiere_token(client):
    assert client.get("/users/me/2fa").status_code == 401
    assert client.post("/users/me/2fa/setup").status_code == 401


def test_secreto_cifrado_y_no_expuesto(client, db, waiter, headers, enabled):
    secret, codes = enabled
    db.refresh(waiter)
    assert waiter.totp_secret and secret not in waiter.totp_secret
    assert all(code not in waiter.totp_recovery_codes for code in codes)
    me = client.get("/auth/me", headers=headers).json()
    assert not any(key.startswith("totp") for key in me)


def test_login_pide_codigo(client, enabled):
    r = _login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["mfa_required"] is True
    assert "access_token" not in body


def test_verify_con_totp_da_jwt(client, enabled):
    secret, _ = enabled
    mfa_token = _login(client).json()["mfa_token"]
    r = _verify(client, mfa_token, pyotp.TOTP(secret).now())
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert client.get("/auth/me", headers=_headers(r.json()["access_token"])).json()["email"] == "waiter@test.com"


def test_verify_con_codigo_malo(client, enabled):
    secret, _ = enabled
    r = _verify(client, _login(client).json()["mfa_token"], _wrong_code(secret))
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_totp_code"


@pytest.mark.parametrize("payload_change", ["caducado", "manipulado", "sin_aud"])
def test_verify_con_mfa_token_no_valido(client, waiter, enabled, payload_change):
    secret, _ = enabled
    payload = {"sub": str(waiter.id), "aud": "2fa", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    key = settings.JWT_SECRET_KEY
    if payload_change == "caducado":
        payload["exp"] = datetime.now(UTC) - timedelta(seconds=1)
    elif payload_change == "manipulado":
        key = "otra-clave-que-no-es-la-buena-000000"
    else:
        del payload["aud"]
    token = jwt.encode(payload, key, algorithm=settings.JWT_ALGORITHM)
    r = _verify(client, token, pyotp.TOTP(secret).now())
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_mfa_token"


def test_mfa_token_no_sirve_como_access_token(client, enabled):
    mfa_token = _login(client).json()["mfa_token"]
    assert client.get("/auth/me", headers=_headers(mfa_token)).status_code == 401


def test_verify_usuario_desactivado(client, db, waiter, enabled):
    secret, _ = enabled
    mfa_token = _login(client).json()["mfa_token"]
    db.refresh(waiter)
    waiter.is_active = False
    db.commit()
    r = _verify(client, mfa_token, pyotp.TOTP(secret).now())
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_mfa_token"


def test_codigo_de_recuperacion_sirve_una_vez(client, headers, enabled):
    _, codes = enabled
    r = _verify(client, _login(client).json()["mfa_token"], codes[0].upper())
    assert r.status_code == 200
    assert client.get("/users/me/2fa", headers=headers).json()["recovery_codes_left"] == 7
    r = _verify(client, _login(client).json()["mfa_token"], codes[0])
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_totp_code"


def test_codigo_de_recuperacion_gastado_en_otra_sesion(db, waiter, enabled):
    _, codes = enabled
    stale = _fresh(db, waiter)
    with TestingSessionLocal() as other:
        assert totp_service._accept_code(other, other.get(User, waiter.id), codes[0]) is True
    assert totp_service._accept_code(db, stale, codes[0]) is False
    assert len(_fresh(db, waiter).totp_recovery_codes.split(",")) == 7


def test_login_social_con_2fa_pide_codigo(client, db, waiter, enabled, monkeypatch):
    monkeypatch.setattr(auth_router.social_auth_service, "login", lambda *_: _fresh(db, waiter))
    r = client.post(
        "/auth/social/google", json={"code": "abc", "redirect_uri": "http://localhost:5173/auth/callback"}
    )
    assert r.status_code == 200
    assert r.json()["mfa_required"] is True


def test_login_social_sin_2fa_igual_que_antes(client, db, waiter, monkeypatch):
    monkeypatch.setattr(auth_router.social_auth_service, "login", lambda *_: _fresh(db, waiter))
    r = client.post(
        "/auth/social/google", json={"code": "abc", "redirect_uri": "http://localhost:5173/auth/callback"}
    )
    assert r.status_code == 200
    assert set(r.json()) == {"access_token", "refresh_token", "token_type"}


def test_login_sin_2fa_igual_que_antes(client, waiter):
    assert set(_login(client).json()) == {"access_token", "refresh_token", "token_type"}


def test_desactivar_con_codigo(client, db, waiter, headers, enabled):
    secret, _ = enabled
    r = client.post("/users/me/2fa/disable", headers=headers, json={"code": pyotp.TOTP(secret).now()})
    assert r.status_code == 200
    assert r.json() == {"enabled": False, "recovery_codes_left": 0}
    db.refresh(waiter)
    assert waiter.totp_secret is None and waiter.totp_recovery_codes is None
    assert "access_token" in _login(client).json()


def test_desactivar_con_codigo_de_recuperacion(client, headers, enabled):
    _, codes = enabled
    r = client.post("/users/me/2fa/disable", headers=headers, json={"code": codes[3]})
    assert r.status_code == 200


def test_desactivar_con_codigo_malo(client, headers, enabled):
    secret, _ = enabled
    r = client.post("/users/me/2fa/disable", headers=headers, json={"code": _wrong_code(secret)})
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_totp_code"


def test_desactivar_sin_2fa(client, headers):
    r = client.post("/users/me/2fa/disable", headers=headers, json={"code": "123456"})
    assert r.status_code == 409
    assert r.json()["code"] == "totp_not_enabled"


def test_codigos_de_recuperacion_largos(enabled):
    _, codes = enabled
    assert all(re.fullmatch(r"[0-9a-f]{10}-[0-9a-f]{10}", code) for code in codes)


def test_totp_enabled_no_admite_nulos(db, waiter):
    db.refresh(waiter)
    assert waiter.totp_enabled is False
    assert User.__table__.c.totp_enabled.nullable is False


def test_si_cambia_la_clave_el_codigo_ya_no_vale(client, enabled, monkeypatch):
    from cryptography.fernet import Fernet

    secret, _ = enabled
    mfa_token = _login(client).json()["mfa_token"]
    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    r = _verify(client, mfa_token, pyotp.TOTP(secret).now())
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_totp_code"


def test_clave_propia_de_cifrado(monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert totp_service._decrypt(totp_service._encrypt("JBSWY3DPEHPK3PXP")) == "JBSWY3DPEHPK3PXP"


def test_el_log_no_incluye_secreto_ni_codigos(client, headers, caplog):
    caplog.set_level(logging.DEBUG)
    secret = client.post("/users/me/2fa/setup", headers=headers).json()["secret"]
    codes = client.post(
        "/users/me/2fa/enable", headers=headers, json={"code": pyotp.TOTP(secret).now()}
    ).json()["recovery_codes"]
    _verify(client, _login(client).json()["mfa_token"], codes[0])
    text = " ".join(f"{r.getMessage()} {r.__dict__}" for r in caplog.records)
    assert secret not in text
    assert all(code not in text for code in codes)
