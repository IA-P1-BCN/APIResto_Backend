import pytest

from app.models.model_user import Role
from tests.test_order import create_test_data
from tests.test_order_items_marks import item_url, order_with_two_lines


@pytest.fixture
def order(client, db, auth_headers):
    table_id, dish_id = create_test_data(db)
    return order_with_two_lines(client, auth_headers(Role.waiter), table_id, dish_id)


def line(response, index=0):
    return response.json()["items"][index]


def test_las_lineas_nuevas_no_tienen_unidades_preparadas_ni_servidas(order):
    assert [(i["prepared_quantity"], i["served_quantity"]) for i in order["items"]] == [(0, 0), (0, 0)]


def test_cocina_prepara_las_unidades_de_una_en_una(client, auth_headers, order):
    kitchen = auth_headers(Role.kitchen)
    r = client.patch(item_url(order), headers=kitchen, json={"prepared_quantity": 1})
    assert r.status_code == 200
    assert line(r)["prepared_quantity"] == 1
    assert line(r)["prepared"] is False

    r = client.patch(item_url(order), headers=kitchen, json={"prepared_quantity": 2})
    assert line(r)["prepared_quantity"] == 2
    assert line(r)["prepared"] is True


def test_sala_sirve_una_de_las_dos_unidades(client, auth_headers, order):
    r = client.patch(item_url(order), headers=auth_headers(Role.waiter), json={"served_quantity": 1})
    assert r.status_code == 200
    assert (line(r)["served_quantity"], line(r)["served"]) == (1, False)


def test_prepared_true_marca_todas_las_unidades_y_false_ninguna(client, auth_headers, order):
    kitchen = auth_headers(Role.kitchen)
    r = client.patch(item_url(order), headers=kitchen, json={"prepared": True})
    assert (line(r)["prepared_quantity"], line(r)["prepared"]) == (2, True)

    r = client.patch(item_url(order), headers=kitchen, json={"prepared": False})
    assert (line(r)["prepared_quantity"], line(r)["prepared"]) == (0, False)


def test_no_se_pueden_marcar_mas_unidades_que_la_cantidad(client, auth_headers, order):
    r = client.patch(item_url(order), headers=auth_headers(Role.kitchen), json={"prepared_quantity": 3})
    assert r.status_code == 422
    assert "quantity" in r.json()["detail"]


@pytest.mark.parametrize(
    "body",
    [{"prepared_quantity": -1}, {"prepared": True, "prepared_quantity": 1}, {"served": True, "served_quantity": 1}],
)
def test_rechaza_cantidades_negativas_o_los_dos_campos_a_la_vez(client, auth_headers, order, body):
    r = client.patch(item_url(order), headers=auth_headers(Role.kitchen), json=body)
    assert r.status_code == 422


@pytest.mark.parametrize(
    ("role", "body"),
    [(Role.waiter, {"prepared_quantity": 1}), (Role.kitchen, {"served_quantity": 1}), (Role.bartender, {"served_quantity": 1})],
)
def test_cada_rol_solo_cuenta_lo_suyo(client, auth_headers, order, role, body):
    r = client.patch(item_url(order), headers=auth_headers(role), json=body)
    assert r.status_code == 403


def test_barra_cuenta_unidades_preparadas(client, db, auth_headers):
    table_id, dish_id = create_test_data(db, station="bar")
    order = order_with_two_lines(client, auth_headers(Role.waiter), table_id, dish_id)
    r = client.patch(item_url(order, 1), headers=auth_headers(Role.bartender), json={"prepared_quantity": 1})
    assert r.status_code == 200
    assert line(r, 1)["prepared"] is True
