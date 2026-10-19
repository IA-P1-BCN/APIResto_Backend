"""HU-33: recuperar la contraseña con forgot-password + set-password (decisiones F, G, I, M, N)."""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from app.config import settings
from app.core.one_time_tokens import hash_token
from app.models.model_password_reset_token import PasswordResetToken
from app.models.model_user import Role, User
from app.services import password_token_service
from app.services.auth_emails import PASSWORD_RESET_SUBJECT

DISPATCHED = {"detail": "If the account exists, an email has been sent"}


def token_from(email) -> str:
    html = email[2]
    link = html.split('href="')[1].split('"')[0].replace("&amp;", "&")
    return parse_qs(urlparse(link).query)["token"][0]


def forgot(client, email):
    return client.post("/auth/forgot-password", json={"email": email})


def set_password(client, token, password="NuevaClave2026"):
    return client.post("/auth/set-password", json={"token": token, "new_password": password})


def login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password})


def tokens_of(db, user_id):
    db.expire_all()
    return db.query(PasswordResetToken).filter_by(user_id=user_id).order_by(PasswordResetToken.id).all()


def test_forgot_password_envia_el_enlace(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")

    r = forgot(client, "Cliente@TEST.com")

    assert r.status_code == 202
    assert r.json() == DISPATCHED
    to, subject, html = outbox[0]
    assert (to, subject) == ("cliente@test.com", PASSWORD_RESET_SUBJECT)
    assert f"{settings.FRONTEND_URL}/restablecer-contrasena?token=" in html
    assert "1 hora" in html
    assert "ignora este email" in html
    record = tokens_of(db, user.id)[0]
    assert record.token_hash == hash_token(token_from(outbox[0]))
    assert record.used_at is None


def test_el_token_de_recuperacion_caduca_en_una_hora(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")

    forgot(client, "cliente@test.com")

    record = tokens_of(db, user.id)[0]
    assert record.expires_at - record.created_at == timedelta(hours=settings.PASSWORD_RESET_EXPIRE_HOURS)
    assert settings.PASSWORD_RESET_EXPIRE_HOURS == 1


def test_forgot_set_password_y_login(client, db, make_user, outbox):
    user = make_user(Role.waiter, email="camarero@test.com")
    forgot(client, "camarero@test.com")

    assert set_password(client, token_from(outbox[0])).status_code == 204

    assert login(client, "camarero@test.com", "NuevaClave2026").status_code == 200
    assert login(client, "camarero@test.com", "secreto123").status_code == 401
    db.expire_all()
    assert db.get(User, user.id).email_verified is True
    assert tokens_of(db, user.id)[0].used_at is not None


def test_el_token_de_recuperacion_es_de_un_solo_uso(client, make_user, outbox):
    make_user(Role.customer, email="cliente@test.com")
    forgot(client, "cliente@test.com")
    token = token_from(outbox[0])
    assert set_password(client, token).status_code == 204

    r = set_password(client, token, "OtraClave2026")

    assert r.status_code == 410
    assert r.json()["code"] == "token_used"


def test_el_token_de_recuperacion_caducado_410(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")
    forgot(client, "cliente@test.com")
    record = tokens_of(db, user.id)[0]
    record.expires_at = record.created_at - timedelta(minutes=1)
    db.commit()

    r = set_password(client, token_from(outbox[0]))

    assert r.status_code == 410
    assert r.json()["code"] == "token_expired"
    assert login(client, "cliente@test.com", "secreto123").status_code == 200


def test_cuenta_sin_contrasena_tambien_recibe_el_enlace(client, db, outbox):
    user = User(name="Social", email="social@test.com", password_hash=None, role=Role.customer.value)
    db.add(user)
    db.commit()

    assert forgot(client, "social@test.com").status_code == 202
    assert len(outbox) == 1
    assert set_password(client, token_from(outbox[0])).status_code == 204
    assert login(client, "social@test.com", "NuevaClave2026").status_code == 200


def test_forgot_email_inexistente_mismo_202_sin_envio(client, outbox, caplog):
    with caplog.at_level("DEBUG"):
        r = forgot(client, "nadie@test.com")

    assert r.status_code == 202
    assert r.json() == DISPATCHED
    assert outbox == []
    assert "nadie@test.com" not in caplog.text


def test_forgot_cuenta_inactiva_mismo_202_sin_envio(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com", is_active=False)

    r = forgot(client, "cliente@test.com")

    assert (r.status_code, r.json()) == (202, DISPATCHED)
    assert outbox == []
    assert tokens_of(db, user.id) == []


def test_forgot_cuenta_borrada_mismo_202_sin_envio(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")
    user.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()

    assert forgot(client, "cliente@test.com").json() == DISPATCHED
    assert outbox == []


def test_forgot_cuenta_verificada_tambien_envia(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")
    user.email_verified = True
    db.commit()

    forgot(client, "cliente@test.com")

    assert len(outbox) == 1


def test_forgot_misma_respuesta_exista_o_no_la_cuenta(client, make_user, outbox):
    make_user(Role.customer, email="cliente@test.com")

    existing = forgot(client, "cliente@test.com")
    missing = forgot(client, "nadie@test.com")

    assert existing.status_code == missing.status_code == 202
    assert existing.content == missing.content
    assert len(outbox) == 1


def test_forgot_dentro_del_tiempo_de_espera_no_envia_otra_vez(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")
    forgot(client, "cliente@test.com")

    r = forgot(client, "cliente@test.com")

    assert (r.status_code, r.json()) == (202, DISPATCHED)
    assert len(outbox) == 1
    assert len(tokens_of(db, user.id)) == 1


def test_forgot_tras_el_tiempo_de_espera_envia_otra_vez(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")
    forgot(client, "cliente@test.com")
    record = tokens_of(db, user.id)[0]
    record.created_at -= timedelta(seconds=settings.TOKEN_RESEND_COOLDOWN_SECONDS + 1)
    db.commit()

    forgot(client, "cliente@test.com")

    assert len(outbox) == 2
    assert len(tokens_of(db, user.id)) == 2


def test_la_invitacion_reciente_tambien_cuenta_para_el_tiempo_de_espera(client, admin_headers, outbox):
    r = client.post("/users/invite", json={"name": "Lucía", "email": "lucia@test.com"}, headers=admin_headers)
    assert r.status_code == 201

    forgot(client, "lucia@test.com")

    assert len(outbox) == 1


def test_usar_el_enlace_nuevo_invalida_el_anterior(client, db, make_user, outbox):
    user = make_user(Role.customer, email="cliente@test.com")
    forgot(client, "cliente@test.com")
    record = tokens_of(db, user.id)[0]
    record.created_at -= timedelta(seconds=settings.TOKEN_RESEND_COOLDOWN_SECONDS + 1)
    db.commit()
    forgot(client, "cliente@test.com")

    assert set_password(client, token_from(outbox[1])).status_code == 204

    r = set_password(client, token_from(outbox[0]), "OtraClave2026")
    assert r.status_code == 410
    assert r.json()["code"] == "token_used"


def test_forgot_email_mal_formado_422(client, outbox):
    assert forgot(client, "no-es-un-email").status_code == 422
    assert outbox == []


def test_forgot_campos_de_mas_422(client, outbox):
    r = client.post("/auth/forgot-password", json={"email": "a@test.com", "role": "admin"})
    assert r.status_code == 422


def test_la_invitacion_sigue_caducando_a_las_48_horas(client, db, admin_headers, outbox):
    r = client.post("/users/invite", json={"name": "Lucía", "email": "lucia@test.com"}, headers=admin_headers)

    record = tokens_of(db, r.json()["id"])[0]
    assert record.expires_at - record.created_at == timedelta(hours=settings.PASSWORD_TOKEN_EXPIRE_HOURS)


def test_ningun_token_ni_contrasena_en_los_logs(client, db, make_user, monkeypatch, caplog):
    """Con el send_email real (EMAIL_ENABLED=false) y un token conocido."""
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)
    monkeypatch.setattr(password_token_service, "generate_token", lambda: "token-recuperacion-secreto")
    user = make_user(Role.customer, email="cliente@test.com")

    with caplog.at_level("DEBUG"):
        forgot(client, "cliente@test.com")
        set_password(client, "token-recuperacion-secreto", "ClaveNuevaPrivada")

    assert "Email simulado" in caplog.text
    assert "token-recuperacion-secreto" not in caplog.text
    assert "restablecer-contrasena" not in caplog.text
    assert "ClaveNuevaPrivada" not in caplog.text
    assert tokens_of(db, user.id)[0].token_hash == hash_token("token-recuperacion-secreto")
    assert login(client, "cliente@test.com", "ClaveNuevaPrivada").status_code == 200
