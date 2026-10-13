import pytest

from app.models.model_user import Role
from tests.test_order import create_test_data


def order_with_two_lines(client, headers, table_id, dish_id):
    r = client.post("/orders/", headers=headers, json={
        "table_id": table_id,
        "items": [
            {"dish_id": dish_id, "quantity": 2},
            {"dish_id": dish_id, "quantity": 1, "notes": "Sin sal"},
        ],
    })
    assert r.status_code == 201, r.text
    return r.json()


def item_url(order, index=0):
    return f"/orders/{order['id']}/items/{order['items'][index]['id']}"


@pytest.fixture
def order(client, db, auth_headers):
    table_id, dish_id = create_test_data(db)
    return order_with_two_lines(client, auth_headers(Role.waiter), table_id, dish_id)


def test_las_lineas_nuevas_no_estan_preparadas_ni_servidas(order):
    assert [(i["prepared"], i["served"]) for i in order["items"]] == [(False, False), (False, False)]


def test_cocina_marca_y_desmarca_un_plato_preparado(client, auth_headers, order):
    kitchen = auth_headers(Role.kitchen)
    r = client.patch(item_url(order), headers=kitchen, json={"prepared": True})
    assert r.status_code == 200
    assert [i["prepared"] for i in r.json()["items"]] == [True, False]
    assert all(not i["served"] for i in r.json()["items"])

    r = client.patch(item_url(order), headers=kitchen, json={"prepared": False})
    assert r.status_code == 200
    assert all(not i["prepared"] for i in r.json()["items"])


def test_sala_marca_y_desmarca_un_plato_servido(client, auth_headers, order):
    waiter = auth_headers(Role.waiter)
    r = client.patch(item_url(order, 1), headers=waiter, json={"served": True})
    assert r.status_code == 200
    assert [i["served"] for i in r.json()["items"]] == [False, True]

    r = client.patch(item_url(order, 1), headers=waiter, json={"served": False})
    assert r.status_code == 200
    assert all(not i["served"] for i in r.json()["items"])

    listed = client.get("/orders/", headers=waiter).json()[0]
    assert all(not i["served"] for i in listed["items"])


def test_admin_marca_las_dos_cosas_a_la_vez(client, auth_headers, order):
    r = client.patch(item_url(order), headers=auth_headers(Role.admin), json={"prepared": True, "served": True})
    assert r.status_code == 200
    assert (r.json()["items"][0]["prepared"], r.json()["items"][0]["served"]) == (True, True)


@pytest.mark.parametrize(
    ("role", "body"),
    [
        (Role.kitchen, {"served": True}),
        (Role.waiter, {"prepared": True}),
        (Role.customer, {"prepared": True}),
        (Role.customer, {"served": True}),
        (Role.kitchen, {"prepared": True, "served": True}),
    ],
)
def test_cada_rol_solo_marca_lo_suyo_403(client, auth_headers, order, role, body):
    r = client.patch(item_url(order), headers=auth_headers(role), json=body)
    assert r.status_code == 403
    after = client.get(f"/orders/{order['id']}", headers=auth_headers(Role.admin)).json()["items"][0]
    assert (after["prepared"], after["served"]) == (False, False)


def test_linea_de_otro_pedido_404(client, db, auth_headers):
    table_id, dish_id = create_test_data(db)
    waiter = auth_headers(Role.waiter)
    a = order_with_two_lines(client, waiter, table_id, dish_id)
    b = order_with_two_lines(client, waiter, table_id, dish_id)
    r = client.patch(f"/orders/{a['id']}/items/{b['items'][0]['id']}", headers=waiter, json={"served": True})
    assert r.status_code == 404


def test_pedido_inexistente_404(client, auth_headers):
    r = client.patch("/orders/999/items/1", headers=auth_headers(Role.kitchen), json={"prepared": True})
    assert r.status_code == 404


@pytest.mark.parametrize("status", ["cancelled", "paid"])
def test_pedido_cerrado_409(client, auth_headers, order, status):
    waiter = auth_headers(Role.waiter)
    steps = ["cancelled"] if status == "cancelled" else ["in_kitchen", "served", "paid"]
    for step in steps:
        assert client.patch(f"/orders/{order['id']}/status", headers=waiter, json={"status": step}).status_code == 200

    assert client.patch(item_url(order), headers=waiter, json={"served": True}).status_code == 409
    assert client.patch(item_url(order), headers=auth_headers(Role.kitchen), json={"prepared": True}).status_code == 409


def test_sin_token_401(client):
    assert client.patch("/orders/1/items/1", json={"served": True}).status_code == 401


@pytest.mark.parametrize("body", [{}, {"served": None}, {"listo": True}])
def test_cuerpo_invalido_422(client, auth_headers, order, body):
    r = client.patch(item_url(order), headers=auth_headers(Role.admin), json=body)
    assert r.status_code == 422
