"""HU-45 / R-16: progreso del pedido (ready_to_serve, stage y by_station)."""

import pytest

from app.models.dining_table import DiningTable
from app.models.model_category import Category
from app.models.model_dish import Dish
from app.models.model_user import Role
from app.schemas.schema_order import StationProgress


@pytest.fixture
def menu(db):
    """Un plato de cocina, una bebida de barra y una mesa."""
    table = DiningTable(number=1, capacity=4, location="terrace")
    main = Category(name="Principales", station="kitchen")
    drinks = Category(name="Bebidas", station="bar")
    db.add_all([table, main, drinks])
    db.flush()
    pasta = Dish(name="Pasta", price=10, category_id=main.id)
    beer = Dish(name="Cerveza", price=3, category_id=drinks.id)
    db.add_all([pasta, beer])
    db.commit()
    return {"table": table.id, "pasta": pasta.id, "beer": beer.id}


@pytest.fixture
def waiter(auth_headers):
    return auth_headers(Role.waiter)


@pytest.fixture
def kitchen(auth_headers):
    return auth_headers(Role.kitchen)


@pytest.fixture
def bartender(auth_headers):
    return auth_headers(Role.bartender)


def place_order(client, headers, menu, **quantities):
    r = client.post("/orders/", headers=headers, json={
        "table_id": menu["table"],
        "items": [{"dish_id": menu[key], "quantity": qty} for key, qty in quantities.items()],
    })
    assert r.status_code == 201, r.text
    return r.json()


def line_id(order, menu, key):
    return next(i["id"] for i in order["items"] if i["dish_id"] == menu[key])


def mark(client, headers, order, item_id, **body):
    r = client.patch(f"/orders/{order['id']}/items/{item_id}", headers=headers, json=body)
    assert r.status_code == 200, r.text
    return r.json()


def progress(quantity, prepared, served, ready, stage):
    return {
        "quantity": quantity,
        "prepared_quantity": prepared,
        "served_quantity": served,
        "ready_to_serve": ready,
        "stage": stage,
    }


def test_un_pedido_nuevo_esta_waiting(client, waiter, menu):
    order = place_order(client, waiter, menu, pasta=2, beer=1)
    assert [i["ready_to_serve"] for i in order["items"]] == [0, 0]
    assert order["progress"] == {
        **progress(3, 0, 0, 0, "waiting"),
        "by_station": {
            "kitchen": progress(2, 0, 0, 0, "waiting"),
            "bar": progress(1, 0, 0, 0, "waiting"),
        },
    }


def test_unidades_preparadas_sin_servir_estan_listas(client, waiter, kitchen, menu):
    order = place_order(client, waiter, menu, pasta=2)
    item = line_id(order, menu, "pasta")
    body = mark(client, kitchen, order, item, prepared_quantity=1)
    assert body["items"][0]["ready_to_serve"] == 1
    assert body["progress"]["stage"] == "ready_to_serve"


def test_preparing_cuando_lo_preparado_ya_esta_servido(client, waiter, kitchen, menu):
    order = place_order(client, waiter, menu, pasta=2)
    item = line_id(order, menu, "pasta")
    mark(client, kitchen, order, item, prepared_quantity=1)
    body = mark(client, waiter, order, item, served_quantity=1)
    assert body["items"][0]["ready_to_serve"] == 0
    assert body["progress"] == {
        **progress(2, 1, 1, 0, "preparing"),
        "by_station": {"kitchen": progress(2, 1, 1, 0, "preparing")},
    }


def test_all_served_cuando_todo_esta_servido(client, waiter, kitchen, menu):
    order = place_order(client, waiter, menu, pasta=2)
    item = line_id(order, menu, "pasta")
    mark(client, kitchen, order, item, prepared=True)
    body = mark(client, waiter, order, item, served=True)
    assert body["progress"]["stage"] == "all_served"
    assert body["progress"]["ready_to_serve"] == 0


def test_algo_servido_y_algo_listo_gana_ready_to_serve(client, waiter, kitchen, bartender, menu):
    order = place_order(client, waiter, menu, pasta=1, beer=1)
    pasta, beer = line_id(order, menu, "pasta"), line_id(order, menu, "beer")
    mark(client, kitchen, order, pasta, prepared=True)
    mark(client, waiter, order, pasta, served=True)
    body = mark(client, bartender, order, beer, prepared=True)
    detail = client.get(f"/orders/{order['id']}", headers=waiter).json()
    assert body["progress"]["stage"] == "ready_to_serve"
    assert detail["progress"]["stage"] == "ready_to_serve"
    assert detail["progress"]["by_station"]["kitchen"]["stage"] == "all_served"
    assert detail["progress"]["by_station"]["bar"]["stage"] == "ready_to_serve"


def test_servir_sin_preparar_no_da_negativos(client, waiter, menu):
    order = place_order(client, waiter, menu, pasta=2)
    body = mark(client, waiter, order, line_id(order, menu, "pasta"), served_quantity=1)
    assert body["items"][0]["ready_to_serve"] == 0
    assert body["progress"] == {
        **progress(2, 0, 1, 0, "preparing"),
        "by_station": {"kitchen": progress(2, 0, 1, 0, "preparing")},
    }


def test_ready_to_serve_suma_las_lineas_y_no_resta_los_totales(client, waiter, bartender, menu):
    order = place_order(client, waiter, menu, pasta=1, beer=1)
    mark(client, waiter, order, line_id(order, menu, "pasta"), served=True)
    body = mark(client, bartender, order, line_id(order, menu, "beer"), prepared=True)
    detail = client.get(f"/orders/{order['id']}", headers=waiter).json()
    assert body["progress"]["ready_to_serve"] == 1
    assert detail["progress"] == {
        **progress(2, 1, 1, 1, "ready_to_serve"),
        "by_station": {
            "kitchen": progress(1, 0, 1, 0, "all_served"),
            "bar": progress(1, 1, 0, 1, "ready_to_serve"),
        },
    }


@pytest.mark.parametrize("role", [Role.admin, Role.waiter])
def test_admin_y_camarero_ven_cocina_y_barra(client, auth_headers, waiter, kitchen, menu, role):
    order = place_order(client, waiter, menu, pasta=2, beer=1)
    mark(client, kitchen, order, line_id(order, menu, "pasta"), prepared_quantity=1)
    listed = client.get("/orders/", headers=auth_headers(role)).json()
    assert listed[0]["progress"] == {
        **progress(3, 1, 0, 1, "ready_to_serve"),
        "by_station": {
            "kitchen": progress(2, 1, 0, 1, "ready_to_serve"),
            "bar": progress(1, 0, 0, 0, "waiting"),
        },
    }


@pytest.mark.parametrize(
    ("role", "station", "expected"),
    [
        (Role.kitchen, "kitchen", progress(2, 1, 0, 1, "ready_to_serve")),
        (Role.bartender, "bar", progress(1, 0, 0, 0, "waiting")),
    ],
)
def test_cocina_y_barra_solo_ven_su_progreso(
    client, auth_headers, waiter, kitchen, menu, role, station, expected
):
    order = place_order(client, waiter, menu, pasta=2, beer=1)
    mark(client, kitchen, order, line_id(order, menu, "pasta"), prepared_quantity=1)
    headers = auth_headers(role)
    listed = client.get("/orders/", headers=headers).json()[0]
    single = client.get(f"/orders/{order['id']}", headers=headers).json()
    for view in (listed, single):
        assert view["progress"] == {**expected, "by_station": {station: expected}}


def test_cambiar_el_status_devuelve_el_progreso(client, waiter, kitchen, menu):
    order = place_order(client, waiter, menu, pasta=1, beer=1)
    mark(client, kitchen, order, line_id(order, menu, "pasta"), prepared=True)
    r = client.patch(f"/orders/{order['id']}/status", headers=kitchen, json={"status": "in_kitchen"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "in_kitchen"
    assert r.json()["progress"] == {
        **progress(1, 1, 0, 1, "ready_to_serve"),
        "by_station": {"kitchen": progress(1, 1, 0, 1, "ready_to_serve")},
    }


def test_un_pedido_cancelado_conserva_su_progreso(client, waiter, kitchen, menu):
    order = place_order(client, waiter, menu, pasta=1)
    mark(client, kitchen, order, line_id(order, menu, "pasta"), prepared=True)
    r = client.patch(f"/orders/{order['id']}/status", headers=waiter, json={"status": "cancelled"})
    assert r.status_code == 200, r.text
    assert r.json()["progress"]["stage"] == "ready_to_serve"


def test_el_progreso_no_cambia_el_status(client, waiter, kitchen, menu):
    order = place_order(client, waiter, menu, pasta=1)
    item = line_id(order, menu, "pasta")
    mark(client, kitchen, order, item, prepared=True)
    body = mark(client, waiter, order, item, served=True)
    assert body["progress"]["stage"] == "all_served"
    assert body["status"] == "pending"


def test_sin_lineas_el_progreso_esta_waiting():
    assert StationProgress.from_items([]).model_dump() == progress(0, 0, 0, 0, "waiting")


def test_sin_token_no_se_ve_el_progreso(client):
    assert client.get("/orders/").status_code == 401


def test_un_cliente_no_ve_el_progreso(client, auth_headers):
    r = client.get("/orders/", headers=auth_headers(Role.customer))
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


def test_cocina_no_ve_el_progreso_de_un_pedido_solo_de_barra(client, waiter, kitchen, menu):
    order = place_order(client, waiter, menu, beer=2)
    r = client.get(f"/orders/{order['id']}", headers=kitchen)
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"
