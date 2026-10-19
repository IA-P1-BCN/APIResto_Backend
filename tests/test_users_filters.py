"""HU-24: filtrar, buscar y paginar usuarios en GET /users/."""

import pytest


@pytest.fixture
def admin(client, admin_headers):
    """Cliente que hace las peticiones como admin."""
    client.headers.update(admin_headers)
    return client


def _create(admin, name, email, role="customer"):
    r = admin.post(
        "/users/",
        json={"name": name, "email": email, "password": "secreto123", "role": role},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def staff(admin):
    """Admin (creado por el fixture) + 4 usuarios de varios roles."""
    return {
        "ana": _create(admin, "Ana Costa", "ana@resto.com", "waiter"),
        "carla": _create(admin, "Carla Ruiz", "carla@resto.com", "bartender"),
        "luis": _create(admin, "Luis Gil", "luis.ana@gmail.com", "waiter"),
        "marta": _create(admin, "Marta Pons", "marta@resto.com", "customer"),
    }


def _emails(response):
    return [u["email"] for u in response.json()["items"]]


def test_list_returns_page_format(admin, staff):
    r = admin.get("/users/")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"items", "total", "page", "size"}
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["size"] == 20


def test_pagination_second_page_and_stable_order(admin, staff):
    first = admin.get("/users/", params={"page": 1, "size": 2}).json()
    second = admin.get("/users/", params={"page": 2, "size": 2}).json()
    ids = [u["id"] for u in first["items"] + second["items"]]
    assert ids == sorted(ids)
    assert len(set(ids)) == 4
    assert first["total"] == second["total"] == 5


def test_page_beyond_last_is_empty(admin, staff):
    r = admin.get("/users/", params={"page": 10, "size": 20})
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 5


@pytest.mark.parametrize("params", [{"size": 101}, {"size": 0}, {"page": 0}])
def test_invalid_pagination_params_return_422(admin, params):
    assert admin.get("/users/", params=params).status_code == 422


def test_skip_and_limit_are_no_longer_used(admin, staff):
    r = admin.get("/users/", params={"skip": 3, "limit": 1})
    assert r.json()["total"] == 5
    assert len(r.json()["items"]) == 5


def test_filter_by_role(admin, staff):
    r = admin.get("/users/", params={"role": "waiter"})
    assert sorted(_emails(r)) == ["ana@resto.com", "luis.ana@gmail.com"]
    assert r.json()["total"] == 2


def test_filter_by_invalid_role_returns_422(admin):
    assert admin.get("/users/", params={"role": "chef"}).status_code == 422


def test_filter_by_is_active(admin, staff):
    admin.patch(f"/users/{staff['carla']['id']}/deactivate")
    inactive = admin.get("/users/", params={"is_active": False})
    active = admin.get("/users/", params={"is_active": True})
    assert _emails(inactive) == ["carla@resto.com"]
    assert "carla@resto.com" not in _emails(active)
    assert active.json()["total"] == 4


def test_without_is_active_lists_active_and_inactive(admin, staff):
    admin.patch(f"/users/{staff['carla']['id']}/deactivate")
    assert "carla@resto.com" in _emails(admin.get("/users/"))


def test_search_by_name_is_partial_and_case_insensitive(admin, staff):
    r = admin.get("/users/", params={"q": "COSTA"})
    assert _emails(r) == ["ana@resto.com"]


def test_search_matches_name_or_email(admin, staff):
    r = admin.get("/users/", params={"q": "ana"})
    assert sorted(_emails(r)) == ["ana@resto.com", "luis.ana@gmail.com"]


def test_search_by_email_domain(admin, staff):
    r = admin.get("/users/", params={"q": "gmail"})
    assert _emails(r) == ["luis.ana@gmail.com"]


def test_search_with_only_spaces_does_not_filter(admin, staff):
    r = admin.get("/users/", params={"q": "   "})
    assert r.json()["total"] == 5


def test_search_treats_wildcards_as_literal_text(admin, staff):
    assert admin.get("/users/", params={"q": "%"}).json()["total"] == 0
    assert admin.get("/users/", params={"q": "_"}).json()["total"] == 0


def test_search_without_matches_returns_empty_page(admin, staff):
    r = admin.get("/users/", params={"q": "nadie"})
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0, "page": 1, "size": 20}


def test_filters_combine(admin, staff):
    r = admin.get("/users/", params={"role": "waiter", "q": "gil"})
    assert _emails(r) == ["luis.ana@gmail.com"]
    assert r.json()["total"] == 1


def test_filters_combine_with_include_deleted(admin, staff):
    admin.delete(f"/users/{staff['ana']['id']}")
    params = {"role": "waiter"}
    assert _emails(admin.get("/users/", params=params)) == ["luis.ana@gmail.com"]
    with_deleted = admin.get("/users/", params={**params, "include_deleted": True})
    assert sorted(_emails(with_deleted)) == ["ana@resto.com", "luis.ana@gmail.com"]


def test_total_counts_filtered_users_across_pages(admin, staff):
    r = admin.get("/users/", params={"q": "resto", "size": 1})
    assert len(r.json()["items"]) == 1
    assert r.json()["total"] == 3


def test_list_users_requires_admin(client, auth_headers):
    r = client.get("/users/", params={"q": "ana"}, headers=auth_headers("waiter"))
    assert r.status_code == 403


@pytest.fixture
def accented(admin):
    """Usuarios con acentos, ñ y mayúsculas acentuadas (revisión de Manon, #126)."""
    return {
        "jose": _create(admin, "José Núñez", "jnunez@resto.com"),
        "angela": _create(admin, "ÁNGELA Pérez", "apz@resto.com"),
        "joao": _create(admin, "João Conceição", "jc@resto.com"),
    }


@pytest.mark.parametrize(
    ("q", "email"),
    [
        ("jose", "jnunez@resto.com"),
        ("José", "jnunez@resto.com"),
        ("nunez", "jnunez@resto.com"),
        ("NÚÑEZ", "jnunez@resto.com"),
        ("angela", "apz@resto.com"),
        ("ángela", "apz@resto.com"),
        ("perez", "apz@resto.com"),
        ("joao", "jc@resto.com"),
        ("conceicao", "jc@resto.com"),
    ],
)
def test_search_ignores_accents_and_case(admin, accented, q, email):
    assert _emails(admin.get("/users/", params={"q": q})) == [email]


def test_search_longer_than_100_chars_returns_422(admin):
    assert admin.get("/users/", params={"q": "a" * 101}).status_code == 422
    assert admin.get("/users/", params={"q": "a" * 100}).status_code == 200
