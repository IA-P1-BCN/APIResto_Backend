import pytest

from app.core.security import create_access_token
from app.models.model_user import User


@pytest.fixture
def admin(client, admin_headers):
    """Cliente que hace las peticiones como admin."""
    client.headers.update(admin_headers)
    return client

def user_data():
    return {
        "name": "Juan Pérez",
        "email": "juan@test.com",
        "password": "secreto123",
        "phone": "600123456"
    }

def test_create_user_success(admin):
    r = admin.post("/users/", json=user_data())
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "juan@test.com"
    assert data["is_active"] is True
    assert data["role"] == "customer"
    assert "password_hash" not in data

def test_create_user_with_role(admin):
    r = admin.post("/users/", json={**user_data(), "role": "waiter"})
    assert r.status_code == 201
    assert r.json()["role"] == "waiter"

def test_create_user_invalid_role(admin):
    r = admin.post("/users/", json={**user_data(), "role": "chef"})
    assert r.status_code == 422

def test_create_user_duplicate_email(admin):
    admin.post("/users/", json=user_data())
    r = admin.post("/users/", json=user_data())
    assert r.status_code == 409

def test_create_user_invalid_data(admin):
    r = admin.post("/users/", json={"name": "", "email": "bad"})
    assert r.status_code == 422

def test_list_users_only_admin(admin):
    r = admin.get("/users/")
    assert r.status_code == 200
    assert [u["email"] for u in r.json()["items"]] == ["admin@test.com"]

def test_list_users_with_data(admin):
    admin.post("/users/", json=user_data())
    r = admin.get("/users/")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2

def test_get_user_by_id(admin):
    user_id = admin.post("/users/", json=user_data()).json()["id"]
    r = admin.get(f"/users/{user_id}")
    assert r.status_code == 200
    assert r.json()["id"] == user_id

def test_get_user_not_found(admin):
    r = admin.get("/users/999")
    assert r.status_code == 404

def test_update_user(admin):
    user_id = admin.post("/users/", json=user_data()).json()["id"]
    r = admin.put(f"/users/{user_id}", json={"name": "Juan Updated"})
    assert r.status_code == 200
    assert r.json()["name"] == "Juan Updated"

def test_update_user_role(admin):
    user_id = admin.post("/users/", json=user_data()).json()["id"]
    r = admin.put(f"/users/{user_id}", json={"role": "kitchen"})
    assert r.status_code == 200
    assert r.json()["role"] == "kitchen"

def test_update_user_duplicate_email(admin):
    admin.post("/users/", json=user_data())
    other_id = admin.post("/users/", json={**user_data(), "email": "other@test.com"}).json()["id"]
    r = admin.put(f"/users/{other_id}", json={"email": "juan@test.com"})
    assert r.status_code == 409

def test_update_user_not_found(admin):
    r = admin.put("/users/999", json={"name": "X"})
    assert r.status_code == 404

def test_deactivate_user(admin):
    user_id = admin.post("/users/", json=user_data()).json()["id"]
    r = admin.patch(f"/users/{user_id}/deactivate")
    assert r.status_code == 200
    assert r.json()["is_active"] is False

def test_deactivate_user_not_found(admin):
    r = admin.patch("/users/999/deactivate")
    assert r.status_code == 404


def _create(admin, **overrides):
    return admin.post("/users/", json={**user_data(), **overrides}).json()


def _admin_id(admin):
    return admin.get("/auth/me").json()["id"]


def test_create_user_records_created_by(admin):
    user = _create(admin)
    assert user["created_by"] == _admin_id(admin)
    assert user["updated_by"] == _admin_id(admin)
    assert user["deleted_at"] is None
    assert user["updated_at"] is not None


def test_update_user_records_updated_by(admin):
    user = _create(admin)
    r = admin.put(f"/users/{user['id']}", json={"name": "Nuevo"})
    assert r.status_code == 200
    assert r.json()["updated_by"] == _admin_id(admin)
    assert r.json()["created_by"] == _admin_id(admin)


def test_deactivate_records_updated_by(admin):
    user = _create(admin)
    r = admin.patch(f"/users/{user['id']}/deactivate")
    assert r.json()["updated_by"] == _admin_id(admin)


def test_delete_user_soft_deletes(admin):
    user = _create(admin)
    r = admin.delete(f"/users/{user['id']}")
    assert r.status_code == 200
    assert r.json()["deleted_at"] is not None
    assert r.json()["is_active"] is False
    assert r.json()["updated_by"] == _admin_id(admin)


def test_deleted_user_hidden_from_list_and_get(admin):
    user = _create(admin)
    admin.delete(f"/users/{user['id']}")
    assert user["email"] not in [u["email"] for u in admin.get("/users/").json()["items"]]
    assert admin.get(f"/users/{user['id']}").status_code == 404


def test_include_deleted_shows_deleted_users(admin):
    user = _create(admin)
    admin.delete(f"/users/{user['id']}")
    listed = admin.get("/users/", params={"include_deleted": True}).json()["items"]
    assert user["email"] in [u["email"] for u in listed]
    r = admin.get(f"/users/{user['id']}", params={"include_deleted": True})
    assert r.status_code == 200


def test_delete_user_not_found(admin):
    assert admin.delete("/users/999").status_code == 404


def test_delete_already_deleted_user_is_404(admin):
    user = _create(admin)
    admin.delete(f"/users/{user['id']}")
    assert admin.delete(f"/users/{user['id']}").status_code == 404


def test_admin_cannot_delete_or_deactivate_self(admin):
    me = _admin_id(admin)
    assert admin.delete(f"/users/{me}").status_code == 403
    assert admin.patch(f"/users/{me}/deactivate").status_code == 403


def test_restore_user(admin):
    user = _create(admin)
    admin.delete(f"/users/{user['id']}")
    r = admin.post(f"/users/{user['id']}/restore")
    assert r.status_code == 200
    assert r.json()["deleted_at"] is None
    assert r.json()["is_active"] is True
    assert user["email"] in [u["email"] for u in admin.get("/users/").json()["items"]]


def test_restore_user_not_deleted_is_409(admin):
    user = _create(admin)
    assert admin.post(f"/users/{user['id']}/restore").status_code == 409


def test_restore_user_not_found(admin):
    assert admin.post("/users/999/restore").status_code == 404


def test_deleted_user_email_stays_reserved(admin):
    user = _create(admin)
    admin.delete(f"/users/{user['id']}")
    r = admin.post("/users/", json=user_data())
    assert r.status_code == 409


def test_deleted_user_cannot_log_in(admin, client):
    user = _create(admin)
    admin.delete(f"/users/{user['id']}")
    r = client.post("/auth/login", data={"username": user["email"], "password": "secreto123"})
    assert r.status_code == 401


def test_restored_user_can_log_in_again(admin, client):
    user = _create(admin)
    admin.delete(f"/users/{user['id']}")
    admin.post(f"/users/{user['id']}/restore")
    r = client.post("/auth/login", data={"username": user["email"], "password": "secreto123"})
    assert r.status_code == 200


def test_delete_and_restore_forbidden_for_non_admin(client, auth_headers):
    headers = auth_headers("waiter")
    assert client.delete("/users/1", headers=headers).status_code == 403
    assert client.post("/users/1/restore", headers=headers).status_code == 403


def _bearer(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _assert_error(r, status_code, code):
    assert r.status_code == status_code
    body = r.json()
    assert body["code"] == code
    assert isinstance(body["detail"], str)


def _login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password})


def _change_password(client, user, current_password, new_password):
    return client.post(
        "/users/me/password",
        json={"current_password": current_password, "new_password": new_password},
        headers=_bearer(user),
    )


def test_update_my_profile_name_and_phone(client, auth_headers):
    headers = auth_headers("customer")
    r = client.patch(
        "/users/me", json={"name": "Nuevo Nombre", "phone": "611222333"}, headers=headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Nuevo Nombre"
    assert data["phone"] == "611222333"
    assert "password_hash" not in data
    me = client.get("/auth/me", headers=headers).json()
    assert me["name"] == "Nuevo Nombre"
    assert me["phone"] == "611222333"


@pytest.mark.parametrize("role", ["customer", "waiter", "admin"])
def test_update_my_profile_allowed_for_any_role(client, auth_headers, role):
    r = client.patch("/users/me", json={"name": f"{role} editado"}, headers=auth_headers(role))
    assert r.status_code == 200
    assert r.json()["name"] == f"{role} editado"
    assert r.json()["role"] == role


def test_update_my_profile_email_is_normalized(client, auth_headers):
    headers = auth_headers("customer")
    r = client.patch("/users/me", json={"email": "  Nuevo.Email@Test.COM "}, headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "nuevo.email@test.com"
    assert client.get("/auth/me", headers=headers).json()["email"] == "nuevo.email@test.com"


def test_update_my_profile_email_of_other_user_is_409(client, auth_headers, make_user):
    make_user("waiter")
    headers = auth_headers("customer")
    r = client.patch("/users/me", json={"email": "WAITER@test.com"}, headers=headers)
    _assert_error(r, 409, "conflict")
    assert set(r.json()) == {"detail", "code"}
    assert client.get("/auth/me", headers=headers).json()["email"] == "customer@test.com"


def test_update_my_profile_email_of_deleted_user_is_409(admin, client, auth_headers):
    user = _create(admin)
    admin.delete(f"/users/{user['id']}")
    r = client.patch(
        "/users/me", json={"email": user["email"]}, headers=auth_headers("customer")
    )
    _assert_error(r, 409, "conflict")


@pytest.mark.parametrize("email", ["customer@test.com", "CUSTOMER@Test.com"])
def test_update_my_profile_own_email_is_ok(client, auth_headers, email):
    r = client.patch("/users/me", json={"email": email}, headers=auth_headers("customer"))
    assert r.status_code == 200
    assert r.json()["email"] == "customer@test.com"


@pytest.mark.parametrize(
    "payload",
    [
        {"role": "admin"},
        {"is_active": False},
        {"name": "Colado", "role": "admin"},
        {"password": "otraclave123"},
    ],
)
def test_update_my_profile_forbidden_fields_are_422(client, auth_headers, payload):
    headers = auth_headers("customer")
    r = client.patch("/users/me", json=payload, headers=headers)
    _assert_error(r, 422, "validation_error")
    me = client.get("/auth/me", headers=headers).json()
    assert me["role"] == "customer"
    assert me["is_active"] is True
    assert me["name"] == "customer test"


@pytest.mark.parametrize(
    "payload",
    [{"name": ""}, {"name": None}, {"email": None}, {"email": "no-es-email"}],
)
def test_update_my_profile_invalid_values_are_422(client, auth_headers, payload):
    r = client.patch("/users/me", json=payload, headers=auth_headers("customer"))
    _assert_error(r, 422, "validation_error")


def test_update_my_profile_null_phone_clears_it(client, auth_headers):
    headers = auth_headers("customer")
    client.patch("/users/me", json={"phone": "600000000"}, headers=headers)
    r = client.patch("/users/me", json={"phone": None}, headers=headers)
    assert r.status_code == 200
    assert r.json()["phone"] is None


def test_update_my_profile_only_changes_sent_fields(client, auth_headers):
    headers = auth_headers("customer")
    client.patch("/users/me", json={"phone": "600000000"}, headers=headers)
    r = client.patch("/users/me", json={"name": "Solo Nombre"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["phone"] == "600000000"
    assert r.json()["email"] == "customer@test.com"


def test_update_my_profile_without_token_is_401(client):
    r = client.patch("/users/me", json={"name": "X"})
    _assert_error(r, 401, "unauthorized")


def test_update_my_profile_records_updated_by_self(client, make_user):
    user = make_user("waiter")
    r = client.patch("/users/me", json={"name": "Yo Mismo"}, headers=_bearer(user))
    assert r.status_code == 200
    assert r.json()["updated_by"] == user.id


def test_change_my_password_success(client, make_user):
    user = make_user("customer")
    r = _change_password(client, user, "secreto123", "nuevaclave456")
    assert r.status_code == 204
    assert r.content == b""
    assert _login(client, user.email, "nuevaclave456").status_code == 200
    assert _login(client, user.email, "secreto123").status_code == 401


def test_change_my_password_records_updated_by_self(client, make_user, db):
    user = make_user("waiter")
    assert _change_password(client, user, "secreto123", "nuevaclave456").status_code == 204
    db.refresh(user)
    assert user.updated_by == user.id
    assert user.password_hash != "nuevaclave456"


def test_change_my_password_wrong_current_is_403(client, make_user):
    user = make_user("customer")
    r = _change_password(client, user, "incorrecta1", "nuevaclave456")
    _assert_error(r, 403, "invalid_current_password")
    assert _login(client, user.email, "secreto123").status_code == 200


def test_change_my_password_too_short_is_422(client, make_user):
    user = make_user("customer")
    r = _change_password(client, user, "secreto123", "corta1")
    _assert_error(r, 422, "validation_error")


def test_change_my_password_same_as_current_is_422(client, make_user):
    user = make_user("customer")
    r = _change_password(client, user, "secreto123", "secreto123")
    _assert_error(r, 422, "same_password")


def test_change_my_password_without_password_set_is_400(client, db):
    user = User(name="Social", email="social@test.com", password_hash=None, role="customer")
    db.add(user)
    db.commit()
    db.refresh(user)
    r = _change_password(client, user, "loquesea1", "nuevaclave456")
    _assert_error(r, 400, "password_not_set")


@pytest.mark.parametrize(
    "payload",
    [
        {"current_password": "secreto123", "new_password": "nuevaclave456", "role": "admin"},
        {"new_password": "nuevaclave456"},
        {"current_password": "", "new_password": "nuevaclave456"},
    ],
)
def test_change_my_password_invalid_body_is_422(client, make_user, payload):
    user = make_user("customer")
    r = client.post("/users/me/password", json=payload, headers=_bearer(user))
    _assert_error(r, 422, "validation_error")


def test_change_my_password_without_token_is_401(client):
    r = client.post(
        "/users/me/password",
        json={"current_password": "secreto123", "new_password": "nuevaclave456"},
    )
    _assert_error(r, 401, "unauthorized")
