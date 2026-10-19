import pytest
from fastapi import status
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.models.model_user import Role
from app.websocket.kitchen import kitchen_manager
from tests.test_order import create_test_data
from tests.test_order_items_marks import item_url, order_with_two_lines


def test_admin_crea_un_usuario_de_barra(client, admin_headers):
    r = client.post("/users/", headers=admin_headers, json={
        "name": "Barra Demo", "email": "barra@test.com", "password": "secreto123", "role": "bartender",
    })
    assert r.status_code == 201
    assert r.json()["role"] == "bartender"


def test_barra_inicia_sesion_y_ve_su_rol(client, make_user):
    make_user(Role.bartender, email="barra@test.com")
    tok = client.post("/auth/login", data={"username": "barra@test.com", "password": "secreto123"}).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200
    assert me.json()["role"] == "bartender"


@pytest.mark.parametrize("url", ["/orders/", "/categories/", "/dishes/"])
def test_barra_puede_ver_pedidos_y_carta(client, auth_headers, url):
    assert client.get(url, headers=auth_headers(Role.bartender)).status_code == 200


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("post", "/orders/"),
        ("get", "/users/"),
        ("get", "/tables"),
        ("get", "/reservations"),
        ("post", "/categories/"),
    ],
)
def test_barra_no_puede_lo_de_otros_roles_403(client, auth_headers, method, url):
    r = client.request(method, url, headers=auth_headers(Role.bartender), json={})
    assert r.status_code == 403


def test_barra_se_conecta_al_websocket(client, make_user):
    user = make_user(Role.bartender)
    with client.websocket_connect(f"/ws/kitchen?token={create_access_token(user.id, user.role)}") as ws:
        assert len(kitchen_manager.active_connections) == 1
        ws.close()


def test_camarero_sigue_sin_websocket(client, make_user):
    user = make_user(Role.waiter)
    with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect(
        f"/ws/kitchen?token={create_access_token(user.id, user.role)}"
    ):
        pass
    assert exc.value.code == status.WS_1008_POLICY_VIOLATION


def test_barra_marca_platos_preparados_pero_no_servidos(client, db, auth_headers):
    table_id, dish_id = create_test_data(db, station="bar")
    order = order_with_two_lines(client, auth_headers(Role.waiter), table_id, dish_id)
    bartender = auth_headers(Role.bartender)
    r = client.patch(item_url(order), headers=bartender, json={"prepared": True})
    assert r.status_code == 200
    assert r.json()["items"][0]["prepared"] is True
    assert client.patch(item_url(order), headers=bartender, json={"served": True}).status_code == 403
