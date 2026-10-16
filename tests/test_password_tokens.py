"""HU-52: invitar a un usuario y que cree su propia contraseña con el enlace del email."""

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.models.model_password_reset_token import PasswordResetToken
from app.models.model_user import Role, User
from app.repositories import password_reset_token_repository
from app.routers import router_password
from app.services import password_token_service
from app.services.password_token_service import hash_token

INVITE = {"name": "Lucía Gómez", "email": "Lucia@Example.com", "phone": "600123456"}


@pytest.fixture
def sent_emails(monkeypatch):
    emails = []
    monkeypatch.setattr(router_password, "send_email", lambda *email: emails.append(email))
    return emails


def token_from(email) -> str:
    html = email[2]
    link = html.split('href="')[1].split('"')[0].replace("&amp;", "&")
    return parse_qs(urlparse(link).query)["token"][0]


def invite(client, auth_headers, sent_emails, **overrides):
    r = client.post("/users/invite", json={**INVITE, **overrides}, headers=auth_headers(Role.admin))
    assert r.status_code == 201, r.text
    return r.json(), token_from(sent_emails[-1])


def set_password(client, token, password="MiClave2026"):
    return client.post("/auth/set-password", json={"token": token, "new_password": password})


def login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_invite_crea_usuario_sin_contrasena_y_envia_el_email(client, db, auth_headers, sent_emails):
    user, _ = invite(client, auth_headers, sent_emails)

    assert user["email"] == "lucia@example.com"
    assert user["role"] == "customer"
    assert user["created_by"] is not None
    assert "password_hash" not in user
    to, subject, html = sent_emails[0]
    assert to == "lucia@example.com"
    assert subject == "Crea tu contraseña de APIResto"
    assert "http://localhost:5173/crear-contrasena?token=" in html
    assert db.get(User, user["id"]).password_hash is None


def test_el_token_se_guarda_con_hash_y_caducidad(client, db, auth_headers, sent_emails):
    user, token = invite(client, auth_headers, sent_emails)

    record = db.query(PasswordResetToken).filter_by(user_id=user["id"]).one()
    assert record.token_hash == hash_token(token)
    assert record.token_hash != token
    assert record.used_at is None
    assert record.expires_at - record.created_at == timedelta(hours=48)


def test_si_falla_el_token_no_se_crea_el_usuario(client, db, auth_headers, sent_emails, monkeypatch):
    def broken_token_factory():
        raise RuntimeError("fallo al crear el token")

    monkeypatch.setattr(password_token_service, "_new_token", broken_token_factory)
    headers = auth_headers(Role.admin)
    failing_client = TestClient(client.app, raise_server_exceptions=False)

    r = failing_client.post("/users/invite", json=INVITE, headers=headers)

    assert r.status_code == 500
    assert db.query(User).filter_by(email="lucia@example.com").first() is None
    assert sent_emails == []


def test_si_falla_al_guardar_el_token_tampoco_queda_el_usuario(client, db, auth_headers, sent_emails, monkeypatch):
    headers = auth_headers(Role.admin)
    original = password_reset_token_repository.add_invited_user

    def failing_commit(session, user, token):
        token.token_hash = None
        return original(session, user, token)

    monkeypatch.setattr(password_reset_token_repository, "add_invited_user", failing_commit)
    failing_client = TestClient(client.app, raise_server_exceptions=False)

    assert failing_client.post("/users/invite", json=INVITE, headers=headers).status_code == 500
    db.expire_all()
    assert db.query(User).filter_by(email="lucia@example.com").first() is None


def test_set_password_bloquea_la_fila_del_token(client, auth_headers, sent_emails, monkeypatch):
    _, token = invite(client, auth_headers, sent_emails)
    calls = []
    original = password_reset_token_repository.get_by_hash_for_update
    monkeypatch.setattr(
        password_reset_token_repository,
        "get_by_hash_for_update",
        lambda session, token_hash: calls.append(token_hash) or original(session, token_hash),
    )

    assert set_password(client, token).status_code == 204
    assert calls == [hash_token(token)]


def test_invite_acepta_un_rol_de_personal(client, auth_headers, sent_emails):
    user, _ = invite(client, auth_headers, sent_emails, email="cocina@example.com", role="kitchen")
    assert user["role"] == "kitchen"


def test_invite_email_repetido_409(client, auth_headers, make_user, sent_emails):
    make_user("waiter", email="lucia@example.com")
    r = client.post("/users/invite", json=INVITE, headers=auth_headers(Role.admin))
    assert r.status_code == 409
    assert r.json()["code"] == "conflict"
    assert sent_emails == []


def test_invite_sin_token_401(client, sent_emails):
    assert client.post("/users/invite", json=INVITE).status_code == 401


def test_invite_solo_admin_403(client, auth_headers, sent_emails):
    r = client.post("/users/invite", json=INVITE, headers=auth_headers(Role.waiter))
    assert r.status_code == 403


def test_invite_email_no_valido_422(client, auth_headers, sent_emails):
    r = client.post(
        "/users/invite", json={**INVITE, "email": "no-es-un-email"}, headers=auth_headers(Role.admin)
    )
    assert r.status_code == 422


def test_el_invitado_no_puede_entrar_antes_de_crear_la_contrasena(client, auth_headers, sent_emails):
    invite(client, auth_headers, sent_emails)
    assert login(client, "lucia@example.com", "").status_code in (401, 422)
    assert login(client, "lucia@example.com", "cualquiera1").status_code == 401


def test_set_password_y_despues_login(client, db, auth_headers, sent_emails):
    user, token = invite(client, auth_headers, sent_emails)

    r = set_password(client, token)

    assert r.status_code == 204
    assert r.content == b""
    assert login(client, "lucia@example.com", "MiClave2026").status_code == 200
    record = db.query(PasswordResetToken).filter_by(user_id=user["id"]).one()
    assert record.used_at is not None


def test_set_password_token_desconocido_400(client):
    r = set_password(client, "token-que-no-existe")
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_token"


def test_set_password_token_usado_410(client, auth_headers, sent_emails):
    _, token = invite(client, auth_headers, sent_emails)
    assert set_password(client, token).status_code == 204

    r = set_password(client, token, "OtraClave2026")

    assert r.status_code == 410
    assert r.json()["code"] == "token_used"
    assert login(client, "lucia@example.com", "MiClave2026").status_code == 200


def test_set_password_token_caducado_410(client, db, auth_headers, sent_emails):
    user, token = invite(client, auth_headers, sent_emails)
    record = db.query(PasswordResetToken).filter_by(user_id=user["id"]).one()
    record.expires_at = record.created_at - timedelta(minutes=1)
    db.commit()

    r = set_password(client, token)

    assert r.status_code == 410
    assert r.json()["code"] == "token_expired"


def test_set_password_contrasena_corta_422(client, auth_headers, sent_emails):
    _, token = invite(client, auth_headers, sent_emails)
    assert set_password(client, token, "corta").status_code == 422


def test_set_password_usuario_desactivado_400(client, db, auth_headers, sent_emails):
    user, token = invite(client, auth_headers, sent_emails)
    db.get(User, user["id"]).is_active = False
    db.commit()

    r = set_password(client, token)

    assert r.status_code == 400
    assert r.json()["code"] == "invalid_token"


def test_usar_un_token_invalida_los_demas_del_usuario(client, db, auth_headers, sent_emails):
    user, first = invite(client, auth_headers, sent_emails)
    second = password_token_service.issue_token(db, db.get(User, user["id"]))

    assert set_password(client, second).status_code == 204

    r = set_password(client, first, "OtraClave2026")
    assert r.status_code == 410
    assert r.json()["code"] == "token_used"


def test_el_email_escapa_el_nombre(client, auth_headers, sent_emails):
    invite(client, auth_headers, sent_emails, name="<b>Lucía</b>")
    assert "&lt;b&gt;Lucía&lt;/b&gt;" in sent_emails[0][2]
