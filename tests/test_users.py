import pytest


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
    assert [u["email"] for u in r.json()] == ["admin@test.com"]

def test_list_users_with_data(admin):
    admin.post("/users/", json=user_data())
    r = admin.get("/users/")
    assert r.status_code == 200
    assert len(r.json()) == 2

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
    assert user["email"] not in [u["email"] for u in admin.get("/users/").json()]
    assert admin.get(f"/users/{user['id']}").status_code == 404


def test_include_deleted_shows_deleted_users(admin):
    user = _create(admin)
    admin.delete(f"/users/{user['id']}")
    listed = admin.get("/users/", params={"include_deleted": True}).json()
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
    assert user["email"] in [u["email"] for u in admin.get("/users/").json()]


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
