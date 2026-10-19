"""HU-40 / R-14: cada línea del pedido va a la estación de la categoría de su plato."""

import json

import pytest

from app.core.security import create_access_token
from app.models.dining_table import DiningTable
from app.models.model_category import Category
from app.models.model_dish import Dish
from app.models.model_user import Role


@pytest.fixture
def menu(db):
    """Un plato de cocina, una bebida y un postre de barra, y una mesa."""
    table = DiningTable(number=1, capacity=4, location="terrace")
    main = Category(name="Principales", station="kitchen")
    drinks = Category(name="Bebidas", station="bar")
    db.add_all([table, main, drinks])
    db.flush()
    pasta = Dish(name="Pasta", price=10, category_id=main.id)
    beer = Dish(name="Cerveza", price=3, category_id=drinks.id)
    db.add_all([pasta, beer])
    db.commit()
    return {"table": table.id, "pasta": pasta.id, "beer": beer.id, "drinks": drinks.id}


def place_order(client, headers, menu, *dish_keys):
    r = client.post("/orders/", headers=headers, json={
        "table_id": menu["table"],
        "items": [{"dish_id": menu[key], "quantity": 1} for key in dish_keys],
    })
    assert r.status_code == 201, r.text
    return r.json()


def dishes_of(order, menu):
    return sorted(i["dish_id"] for i in order["items"])


def test_cada_linea_expone_su_estacion(client, auth_headers, menu):
    order = place_order(client, auth_headers(Role.waiter), menu, "pasta", "beer")
    assert {i["dish_id"]: i["station"] for i in order["items"]} == {
        menu["pasta"]: "kitchen", menu["beer"]: "bar",
    }


@pytest.mark.parametrize(("role", "dish"), [(Role.kitchen, "pasta"), (Role.bartender, "beer")])
def test_cocina_y_barra_solo_ven_sus_lineas(client, auth_headers, menu, role, dish):
    order = place_order(client, auth_headers(Role.waiter), menu, "pasta", "beer")
    listed = client.get("/orders/", headers=auth_headers(role)).json()
    single = client.get(f"/orders/{order['id']}", headers=auth_headers(role)).json()
    assert [dishes_of(o, menu) for o in listed] == [[menu[dish]]]
    assert dishes_of(single, menu) == [menu[dish]]


@pytest.mark.parametrize("role", [Role.admin, Role.waiter])
def test_admin_y_camarero_ven_el_pedido_completo(client, auth_headers, menu, role):
    place_order(client, auth_headers(Role.waiter), menu, "pasta", "beer")
    listed = client.get("/orders/", headers=auth_headers(role)).json()
    assert dishes_of(listed[0], menu) == sorted([menu["pasta"], menu["beer"]])


def test_el_total_es_el_del_pedido_completo(client, auth_headers, menu):
    place_order(client, auth_headers(Role.waiter), menu, "pasta", "beer")
    listed = client.get("/orders/", headers=auth_headers(Role.bartender)).json()
    assert float(listed[0]["total"]) == 13


def test_un_pedido_sin_lineas_de_la_estacion_no_aparece(client, auth_headers, menu):
    only_drinks = place_order(client, auth_headers(Role.waiter), menu, "beer")
    kitchen = auth_headers(Role.kitchen)
    assert client.get("/orders/", headers=kitchen).json() == []
    r = client.get(f"/orders/{only_drinks['id']}", headers=kitchen)
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"


def test_la_paginacion_cuenta_solo_pedidos_de_la_estacion(client, auth_headers, menu):
    waiter = auth_headers(Role.waiter)
    first = place_order(client, waiter, menu, "beer")
    place_order(client, waiter, menu, "pasta")
    third = place_order(client, waiter, menu, "beer")
    r = client.get("/orders/?limit=1&skip=1", headers=auth_headers(Role.bartender))
    assert [o["id"] for o in r.json()] == [third["id"]]
    assert first["id"] < third["id"]


@pytest.mark.parametrize(
    ("role", "own", "other"), [(Role.kitchen, 0, 1), (Role.bartender, 1, 0)]
)
def test_marcar_una_linea_de_otra_estacion_da_403(client, auth_headers, menu, role, own, other):
    order = place_order(client, auth_headers(Role.waiter), menu, "pasta", "beer")
    lines = sorted(order["items"], key=lambda i: i["dish_id"] != menu["pasta"])
    base = f"/orders/{order['id']}/items"
    headers = auth_headers(role)
    refused = client.patch(f"{base}/{lines[other]['id']}", headers=headers, json={"prepared": True})
    assert refused.status_code == 403
    assert refused.json()["code"] == "forbidden"
    accepted = client.patch(f"{base}/{lines[own]['id']}", headers=headers, json={"prepared": True})
    assert accepted.status_code == 200
    assert [i["station"] for i in accepted.json()["items"]] == [lines[own]["station"]]


def test_admin_marca_lineas_de_cualquier_estacion(client, auth_headers, menu):
    order = place_order(client, auth_headers(Role.waiter), menu, "pasta", "beer")
    for line in order["items"]:
        r = client.patch(
            f"/orders/{order['id']}/items/{line['id']}",
            headers=auth_headers(Role.admin),
            json={"prepared": True},
        )
        assert r.status_code == 200


def test_cambiar_la_estacion_de_la_categoria_cambia_las_lineas_abiertas(client, auth_headers, menu):
    place_order(client, auth_headers(Role.waiter), menu, "beer")
    admin = auth_headers(Role.admin)
    assert client.get("/orders/", headers=auth_headers(Role.bartender)).json() != []
    client.put(f"/categories/{menu['drinks']}", headers=admin, json={"station": "kitchen"})
    assert client.get("/orders/", headers=auth_headers(Role.bartender)).json() == []
    assert len(client.get("/orders/", headers=auth_headers(Role.kitchen)).json()) == 1


def ws_url(user):
    return f"/ws/kitchen?token={create_access_token(user.id, user.role)}"


def test_el_websocket_envia_a_cada_rol_solo_sus_lineas(client, auth_headers, make_user, menu):
    kitchen, bartender = make_user(Role.kitchen), make_user(Role.bartender)
    with (
        client.websocket_connect(ws_url(kitchen)) as kitchen_ws,
        client.websocket_connect(ws_url(bartender)) as bar_ws,
    ):
        place_order(client, auth_headers(Role.waiter), menu, "pasta", "beer")
        seen = {
            "kitchen": json.loads(kitchen_ws.receive_text())["order"],
            "bar": json.loads(bar_ws.receive_text())["order"],
        }
    assert [i["dish_id"] for i in seen["kitchen"]["items"]] == [menu["pasta"]]
    assert [i["dish_id"] for i in seen["bar"]["items"]] == [menu["beer"]]
    assert seen["kitchen"]["items"][0]["station"] == "kitchen"


def test_el_cambio_de_estado_solo_llega_a_las_estaciones_del_pedido(
    client, auth_headers, make_user, menu
):
    bartender = make_user(Role.bartender)
    order = place_order(client, auth_headers(Role.waiter), menu, "pasta")
    with client.websocket_connect(ws_url(bartender)) as bar_ws:
        client.patch(
            f"/orders/{order['id']}/status", headers=auth_headers(Role.waiter), json={"status": "in_kitchen"}
        )
        place_order(client, auth_headers(Role.waiter), menu, "beer")
        event = json.loads(bar_ws.receive_text())
    assert event["event"] == "order_created"


def test_cambiar_el_estado_de_un_pedido_ajeno_a_la_estacion_da_404(client, auth_headers, menu):
    only_drinks = place_order(client, auth_headers(Role.waiter), menu, "beer")
    url = f"/orders/{only_drinks['id']}/status"
    refused = client.patch(url, headers=auth_headers(Role.kitchen), json={"status": "in_kitchen"})
    assert refused.status_code == 404
    accepted = client.patch(url, headers=auth_headers(Role.bartender), json={"status": "in_kitchen"})
    assert accepted.status_code == 200
    assert [i["station"] for i in accepted.json()["items"]] == ["bar"]
