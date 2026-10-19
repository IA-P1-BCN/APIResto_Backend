from app.core.security import create_access_token


def me_headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_update_my_profile(client, make_user):
    user = make_user("waiter", email="pepe@test.com")
    r = client.patch("/users/me", json={"name": "Pepe Nuevo", "phone": "600111222"}, headers=me_headers(user))
    assert r.status_code == 200
    assert r.json()["name"] == "Pepe Nuevo"
    assert r.json()["phone"] == "600111222"
    assert r.json()["updated_by"] == user.id
    assert "password_hash" not in r.json()


def test_update_my_email_normalizado(client, make_user):
    user = make_user("customer", email="pepe@test.com")
    r = client.patch("/users/me", json={"email": "Pepe@TEST.com"}, headers=me_headers(user))
    assert r.status_code == 200
    assert r.json()["email"] == "pepe@test.com"


def test_update_my_email_duplicado_409(client, make_user):
    make_user("admin", email="otro@test.com")
    user = make_user("customer", email="pepe@test.com")
    r = client.patch("/users/me", json={"email": "otro@test.com"}, headers=me_headers(user))
    assert r.status_code == 409


def test_update_my_profile_rechaza_el_rol(client, make_user):
    user = make_user("customer", email="pepe@test.com")
    r = client.patch("/users/me", json={"role": "admin"}, headers=me_headers(user))
    assert r.status_code == 422
    assert client.get("/auth/me", headers=me_headers(user)).json()["role"] == "customer"


def test_update_my_profile_sin_token_401(client):
    assert client.patch("/users/me", json={"name": "X"}).status_code == 401


def test_change_password_success(client, make_user):
    user = make_user("waiter", email="pepe@test.com")
    r = client.post(
        "/users/me/password",
        json={"current_password": "secreto123", "new_password": "nuevaClave1"},
        headers=me_headers(user),
    )
    assert r.status_code == 204
    assert r.content == b""
    assert login(client, "pepe@test.com", "nuevaClave1").status_code == 200
    assert login(client, "pepe@test.com", "secreto123").status_code == 401


def test_change_password_actual_incorrecta_403(client, make_user):
    user = make_user("waiter", email="pepe@test.com")
    r = client.post(
        "/users/me/password",
        json={"current_password": "mal", "new_password": "nuevaClave1"},
        headers=me_headers(user),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "invalid_current_password"


def test_change_password_corta_422(client, make_user):
    user = make_user("waiter", email="pepe@test.com")
    r = client.post(
        "/users/me/password",
        json={"current_password": "secreto123", "new_password": "corta"},
        headers=me_headers(user),
    )
    assert r.status_code == 422


def test_change_password_sin_token_401(client):
    r = client.post("/users/me/password", json={"current_password": "x", "new_password": "nuevaClave1"})
    assert r.status_code == 401
