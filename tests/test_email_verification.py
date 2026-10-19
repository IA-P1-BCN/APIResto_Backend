"""HU-33: verificación de email (R-15, informativa) con tokens de un solo uso (R-09)."""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.config import settings
from app.core.one_time_tokens import hash_token
from app.core.security import create_access_token
from app.models.model_email_verification_token import EmailVerificationToken
from app.models.model_user import Role, User
from app.schemas.schema_social import SocialProfile
from app.scripts.create_admin import create_admin
from app.services import email_verification_service, social_providers
from app.services.auth_emails import VERIFICATION_SUBJECT

REGISTER = {"name": "Ana Gómez", "email": "Ana@Example.com", "password": "secreto123"}
DISPATCHED = {"detail": "If the account exists, an email has been sent"}
REDIRECT = "http://localhost:5173/auth/callback"


def token_from(email) -> str:
    html = email[2]
    link = html.split('href="')[1].split('"')[0].replace("&amp;", "&")
    return parse_qs(urlparse(link).query)["token"][0]


def register(client, outbox, **overrides):
    r = client.post("/auth/register", json={**REGISTER, **overrides})
    assert r.status_code == 201, r.text
    return r.json(), token_from(outbox[-1])


def verify(client, token):
    return client.post("/auth/verify-email", json={"token": token})


def resend(client, email):
    return client.post("/auth/resend-verification", json={"email": email})


def login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password})


def me_headers(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id, 'customer')}"}


def tokens_of(db, user_id):
    db.expire_all()
    return db.query(EmailVerificationToken).filter_by(user_id=user_id).order_by(EmailVerificationToken.id).all()


def leave_cooldown(db, user_id):
    for record in tokens_of(db, user_id):
        record.created_at -= timedelta(seconds=settings.TOKEN_RESEND_COOLDOWN_SECONDS + 1)
    db.commit()


def is_verified(db, user_id) -> bool:
    db.expire_all()
    return db.get(User, user_id).email_verified


def test_register_nace_sin_verificar_y_envia_el_email(client, db, outbox):
    user, _ = register(client, outbox)

    assert user["email_verified"] is False
    assert "password_hash" not in user
    to, subject, html = outbox[0]
    assert to == "ana@example.com"
    assert subject == VERIFICATION_SUBJECT
    assert f"{settings.FRONTEND_URL}/verificar-email?token=" in html
    assert f"{settings.EMAIL_VERIFY_EXPIRE_HOURS} horas" in html
    assert not is_verified(db, user["id"])


def test_el_token_se_guarda_con_hash_y_caduca_a_las_48_horas(client, db, outbox):
    user, token = register(client, outbox)

    record = tokens_of(db, user["id"])[0]
    assert record.token_hash == hash_token(token)
    assert record.token_hash != token
    assert record.used_at is None
    assert record.expires_at - record.created_at == timedelta(hours=settings.EMAIL_VERIFY_EXPIRE_HOURS)


def test_verify_email_marca_la_cuenta_como_verificada(client, db, outbox):
    user, token = register(client, outbox)

    r = verify(client, token)

    assert r.status_code == 204
    assert r.content == b""
    assert is_verified(db, user["id"])
    record = tokens_of(db, user["id"])[0]
    assert record.used_at is not None
    assert db.get(User, user["id"]).updated_by == user["id"]


def test_verify_email_se_ve_en_auth_me(client, outbox):
    user, token = register(client, outbox)
    verify(client, token)

    me = client.get("/auth/me", headers=me_headers(user["id"])).json()

    assert me["email_verified"] is True
    assert "password_hash" not in me


def test_verify_email_token_desconocido_400(client):
    r = verify(client, "token-que-no-existe")
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_token"


def test_verify_email_token_usado_410(client, outbox):
    _, token = register(client, outbox)
    assert verify(client, token).status_code == 204

    r = verify(client, token)

    assert r.status_code == 410
    assert r.json()["code"] == "token_used"


def test_verify_email_token_caducado_410(client, db, outbox):
    user, token = register(client, outbox)
    record = tokens_of(db, user["id"])[0]
    record.expires_at = record.created_at - timedelta(minutes=1)
    db.commit()

    r = verify(client, token)

    assert r.status_code == 410
    assert r.json()["code"] == "token_expired"
    assert not is_verified(db, user["id"])


def test_verify_email_usuario_desactivado_400(client, db, outbox):
    user, token = register(client, outbox)
    db.get(User, user["id"]).is_active = False
    db.commit()

    r = verify(client, token)

    assert r.status_code == 400
    assert r.json()["code"] == "invalid_token"
    assert not is_verified(db, user["id"])


def test_verify_email_usuario_borrado_400(client, db, outbox):
    user, token = register(client, outbox)
    db.get(User, user["id"]).deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()

    r = verify(client, token)

    assert r.status_code == 400
    assert r.json()["code"] == "invalid_token"


def test_verify_email_cuenta_ya_verificada_204_y_consume_el_token(client, db, outbox):
    user, token = register(client, outbox)
    db.get(User, user["id"]).email_verified = True
    db.commit()

    assert verify(client, token).status_code == 204
    assert tokens_of(db, user["id"])[0].used_at is not None
    assert verify(client, token).json()["code"] == "token_used"


def test_usar_un_token_invalida_los_demas_del_usuario(client, db, outbox):
    user, first = register(client, outbox)
    second = email_verification_service.issue_verification_token(db, db.get(User, user["id"]))

    assert verify(client, second).status_code == 204

    r = verify(client, first)
    assert r.status_code == 410
    assert r.json()["code"] == "token_used"
    assert all(record.used_at is not None for record in tokens_of(db, user["id"]))


def test_verify_email_sin_token_422(client):
    assert client.post("/auth/verify-email", json={}).status_code == 422


def test_verify_email_campos_de_mas_422(client):
    assert client.post("/auth/verify-email", json={"token": "x", "email": "a@b.com"}).status_code == 422


def test_resend_cuenta_sin_verificar_envia_otro_enlace(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")

    r = resend(client, "Cliente@TEST.com")

    assert r.status_code == 202
    assert r.json() == DISPATCHED
    to, subject, _ = outbox[0]
    assert (to, subject) == ("cliente@test.com", VERIFICATION_SUBJECT)
    token = token_from(outbox[0])
    assert tokens_of(db, user.id)[0].token_hash == hash_token(token)
    assert verify(client, token).status_code == 204
    assert is_verified(db, user.id)


def test_resend_tras_el_tiempo_de_espera_envia(client, db, outbox):
    user, _ = register(client, outbox)
    leave_cooldown(db, user["id"])

    assert resend(client, "ana@example.com").status_code == 202
    assert len(outbox) == 2
    assert len(tokens_of(db, user["id"])) == 2


def test_resend_dentro_del_tiempo_de_espera_no_envia(client, db, outbox):
    user, _ = register(client, outbox)

    r = resend(client, "ana@example.com")

    assert r.status_code == 202
    assert r.json() == DISPATCHED
    assert len(outbox) == 1
    assert len(tokens_of(db, user["id"])) == 1


def test_resend_email_inexistente_mismo_202_sin_envio(client, outbox, caplog):
    with caplog.at_level("DEBUG"):
        r = resend(client, "nadie@test.com")

    assert r.status_code == 202
    assert r.json() == DISPATCHED
    assert outbox == []
    assert "nadie@test.com" not in caplog.text


def test_resend_cuenta_verificada_mismo_202_sin_envio(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")
    user.email_verified = True
    db.commit()

    r = resend(client, "cliente@test.com")

    assert (r.status_code, r.json()) == (202, DISPATCHED)
    assert outbox == []


def test_resend_cuenta_inactiva_mismo_202_sin_envio(client, make_user, outbox):
    make_user(Role.customer, email="cliente@test.com", is_active=False)

    r = resend(client, "cliente@test.com")

    assert (r.status_code, r.json()) == (202, DISPATCHED)
    assert outbox == []


def test_resend_cuenta_borrada_mismo_202_sin_envio(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")
    user.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()

    assert resend(client, "cliente@test.com").json() == DISPATCHED
    assert outbox == []


def test_resend_misma_respuesta_exista_o_no_la_cuenta(client, make_user, outbox):
    make_user(Role.customer, email="cliente@test.com")

    existing = resend(client, "cliente@test.com")
    missing = resend(client, "nadie@test.com")

    assert existing.status_code == missing.status_code == 202
    assert existing.content == missing.content
    assert len(outbox) == 1


def test_resend_email_mal_formado_422(client, outbox):
    assert resend(client, "no-es-un-email").status_code == 422
    assert outbox == []


def test_login_sin_verificar_200(client, outbox):
    user, _ = register(client, outbox)
    assert user["email_verified"] is False

    assert login(client, "ana@example.com", "secreto123").status_code == 200


def test_alta_por_admin_nace_verificada(client, admin_headers, outbox):
    r = client.post(
        "/users/",
        json={"name": "Juan Pérez", "email": "juan@test.com", "password": "secreto123"},
        headers=admin_headers,
    )

    assert r.status_code == 201
    assert r.json()["email_verified"] is True
    assert "password_hash" not in r.json()
    assert outbox == []


def test_invitado_queda_verificado_tras_set_password(client, db, admin_headers, outbox):
    r = client.post(
        "/users/invite", json={"name": "Lucía", "email": "lucia@test.com"}, headers=admin_headers
    )
    assert r.status_code == 201
    assert r.json()["email_verified"] is False

    assert client.post(
        "/auth/set-password", json={"token": token_from(outbox[-1]), "new_password": "MiClave2026"}
    ).status_code == 204

    assert is_verified(db, r.json()["id"])


def test_create_admin_nace_verificado(db):
    assert create_admin(db, "jefa@test.com", "secreto123", "Jefa").email_verified is True


def test_create_admin_verifica_al_promover(db, make_user):
    customer = make_user(Role.customer, email="cliente@test.com")
    assert customer.email_verified is False

    assert create_admin(db, "cliente@test.com", "secreto123").email_verified is True


@pytest.fixture
def social_profile(monkeypatch):
    """Sustituye al proveedor OAuth: devuelve un perfil de Google con el email verificado."""
    profile = SocialProfile(provider_user_id="g-1", email="Ana@Gmail.com", email_verified=True, name="Ana")
    monkeypatch.setattr(social_providers, "fetch_profile", lambda provider, code, redirect_uri: profile)
    return profile


def social_login(client):
    return client.post("/auth/social/google", json={"code": "abc123", "redirect_uri": REDIRECT})


def test_login_social_cuenta_nueva_nace_verificada(client, db, social_profile):
    assert social_login(client).status_code == 200
    assert db.query(User).filter_by(email="ana@gmail.com").one().email_verified is True


def test_login_social_vincula_y_verifica_la_cuenta(client, db, make_user, social_profile):
    user = make_user(Role.customer, email="ana@gmail.com")
    assert user.email_verified is False

    assert social_login(client).status_code == 200
    assert is_verified(db, user.id)


def test_cambiar_el_email_pide_verificarlo_de_nuevo(client, db, outbox):
    user, old_token = register(client, outbox)
    db.get(User, user["id"]).email_verified = True
    db.commit()

    r = client.patch("/users/me", json={"email": "Nueva@Example.com"}, headers=me_headers(user["id"]))

    assert r.status_code == 200
    assert r.json()["email"] == "nueva@example.com"
    assert r.json()["email_verified"] is False
    assert len(outbox) == 2
    to, subject, _ = outbox[-1]
    assert (to, subject) == ("nueva@example.com", VERIFICATION_SUBJECT)
    new_token = token_from(outbox[-1])
    assert verify(client, old_token).json()["code"] == "token_used"
    assert verify(client, new_token).status_code == 204
    assert is_verified(db, user["id"])


def test_cambiar_el_email_no_espera_el_tiempo_de_espera(client, db, outbox):
    user, _ = register(client, outbox)

    client.patch("/users/me", json={"email": "nueva@example.com"}, headers=me_headers(user["id"]))

    assert len(outbox) == 2
    assert len(tokens_of(db, user["id"])) == 2


def test_mismo_email_no_cambia_nada(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")
    user.email_verified = True
    db.commit()

    r = client.patch("/users/me", json={"email": "Cliente@test.com", "name": "Otro"}, headers=me_headers(user.id))

    assert r.status_code == 200
    assert r.json()["email_verified"] is True
    assert outbox == []
    assert tokens_of(db, user.id) == []


def test_editar_el_perfil_sin_email_no_envia(client, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")

    r = client.patch("/users/me", json={"name": "Otro"}, headers=me_headers(user.id))

    assert r.status_code == 200
    assert outbox == []


def test_cambiar_el_email_a_uno_repetido_409_sin_envio(client, make_user, outbox):
    make_user(Role.waiter, email="otro@test.com")
    user = make_user(Role.customer, email="cliente@test.com")

    r = client.patch("/users/me", json={"email": "otro@test.com"}, headers=me_headers(user.id))

    assert r.status_code == 409
    assert outbox == []


def test_ningun_token_en_claro_en_la_bd_ni_en_los_logs(client, db, make_user, monkeypatch, caplog):
    """Con el send_email real (EMAIL_ENABLED=false) y un token conocido."""
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)
    tokens = iter(["token-registro-secreto", "token-resend-secreto", "token-email-nuevo-secreto"])
    monkeypatch.setattr(email_verification_service, "generate_token", lambda: next(tokens))

    with caplog.at_level("DEBUG"):
        user = client.post("/auth/register", json=REGISTER).json()
        leave_cooldown(db, user["id"])
        resend(client, "ana@example.com")
        client.patch("/users/me", json={"email": "nueva@example.com"}, headers=me_headers(user["id"]))
        verify(client, "token-email-nuevo-secreto")
        verify(client, "token-registro-secreto")

    stored = {record.token_hash for record in tokens_of(db, user["id"])}
    assert stored == {
        hash_token(t) for t in ("token-registro-secreto", "token-resend-secreto", "token-email-nuevo-secreto")
    }
    assert "Email simulado" in caplog.text
    assert "Email verified" in caplog.text
    assert "secreto" not in caplog.text
    assert "verificar-email" not in caplog.text
    assert "secreto123" not in caplog.text


def alembic_config(url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.attributes["configure_logger"] = False
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_la_migracion_0009_marca_verificadas_las_cuentas_existentes(tmp_path):
    url = f"sqlite:///{(tmp_path / 'verificacion.db').as_posix()}"
    cfg = alembic_config(url)
    command.upgrade(cfg, "0008")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO users (name, email, password_hash, role, is_active) VALUES "
            "('Antes', 'antes@test.com', 'x', 'customer', 1)"
        ))

    command.upgrade(cfg, "0009")
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO users (name, email, password_hash, role, is_active) VALUES "
            "('Después', 'despues@test.com', 'x', 'customer', 1)"
        ))
        verified = dict(conn.execute(text("SELECT email, email_verified FROM users")).all())
    engine.dispose()

    assert verified == {"antes@test.com": 1, "despues@test.com": 0}
