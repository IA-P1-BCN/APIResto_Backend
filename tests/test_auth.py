from app.core.security import create_access_token
from app.models.model_user import Role


def login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password})


def register_data():
    return {"name": "Ana Gómez", "email": "ana@test.com", "password": "secreto123"}


def register(client, **overrides):
    return client.post("/auth/register", json={**register_data(), **overrides})


def test_login_success(client, make_user):
    make_user(Role.waiter, email="test@test.com")
    r = login(client, "test@test.com", "secreto123")
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_token_sirve_para_me(client, make_user):
    make_user(Role.waiter, email="test@test.com")
    token = login(client, "test@test.com", "secreto123").json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "test@test.com"
    assert r.json()["role"] == "waiter"


def test_login_wrong_password(client, make_user):
    make_user(Role.waiter, email="test@test.com")
    r = login(client, "test@test.com", "wrong")
    assert r.status_code == 401


def test_login_user_not_found(client):
    r = login(client, "nobody@test.com", "pass")
    assert r.status_code == 401


def test_login_usuario_desactivado_401(client, make_user):
    make_user(Role.waiter, email="test@test.com", is_active=False)
    r = login(client, "test@test.com", "secreto123")
    assert r.status_code == 401


def test_get_me_success(client, make_user):
    user = make_user(Role.customer, email="test@test.com")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {create_access_token(user.id, user.role)}"})
    assert r.status_code == 200
    assert r.json()["email"] == "test@test.com"
    assert "password_hash" not in r.json()


def test_get_me_invalid_token(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer token_falso"})
    assert r.status_code == 401


def test_get_me_no_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_register_success(client):
    r = register(client)
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "ana@test.com"
    assert data["role"] == "customer"
    assert data["is_active"] is True
    assert "password_hash" not in data
    assert "access_token" not in data


def test_register_guarda_el_email_en_minusculas(client):
    r = register(client, email="Ana@TEST.com")
    assert r.status_code == 201
    assert r.json()["email"] == "ana@test.com"


def test_register_email_duplicado_409(client):
    register(client)
    r = register(client)
    assert r.status_code == 409
    assert r.json()["code"] == "conflict"


def test_register_email_duplicado_ignora_mayusculas_409(client):
    register(client, email="ana@test.com")
    r = register(client, email="ANA@test.com")
    assert r.status_code == 409


def test_register_ignora_el_rol_del_payload(client):
    r = register(client, role="admin")
    assert r.status_code == 201
    assert r.json()["role"] == "customer"


def test_register_password_corta_422(client):
    r = register(client, password="corta")
    assert r.status_code == 422


def test_register_email_invalido_422(client):
    r = register(client, email="no-es-un-email")
    assert r.status_code == 422


def test_register_datos_incompletos_422(client):
    r = client.post("/auth/register", json={"email": "ana@test.com"})
    assert r.status_code == 422


def test_register_permite_login_despues(client):
    register(client)
    r = login(client, "ana@test.com", "secreto123")
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_register_permite_login_con_email_en_otra_caja(client):
    register(client, email="ana@test.com")
    r = login(client, "Ana@Test.com", "secreto123")
    assert r.status_code == 200
