"""Tests unitarios de KitchenConnectionManager (app/websocket/kitchen.py)."""

import asyncio
import json

import pytest

from app.websocket.kitchen import KitchenConnectionManager


class FakeWebSocket:
    """WebSocket mínimo: guarda lo enviado o falla al enviar."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.accepted = False
        self.sent: list[str] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, text: str) -> None:
        if self.error:
            raise self.error
        self.sent.append(text)


def _connect(manager: KitchenConnectionManager, *sockets: FakeWebSocket) -> None:
    for ws in sockets:
        asyncio.run(manager.connect(ws))


def test_connect_accepts_and_registers():
    manager = KitchenConnectionManager()
    ws = FakeWebSocket()

    _connect(manager, ws)

    assert ws.accepted
    assert manager.active_connections == [ws]


def test_broadcast_sends_json_to_every_connection():
    manager = KitchenConnectionManager()
    first, second = FakeWebSocket(), FakeWebSocket()
    _connect(manager, first, second)

    asyncio.run(manager.broadcast({"event": "order_created", "order": {"id": 1}}))

    for ws in (first, second):
        assert json.loads(ws.sent[0]) == {"event": "order_created", "order": {"id": 1}}


@pytest.mark.parametrize("error", [RuntimeError("cerrado"), ConnectionError("caído")])
def test_broadcast_drops_broken_connections_and_keeps_the_rest(error):
    manager = KitchenConnectionManager()
    broken, alive = FakeWebSocket(error), FakeWebSocket()
    _connect(manager, broken, alive)

    asyncio.run(manager.broadcast({"event": "order_status_changed"}))

    assert manager.active_connections == [alive]
    assert len(alive.sent) == 1


def test_disconnect_unknown_connection_does_nothing():
    manager = KitchenConnectionManager()

    manager.disconnect(FakeWebSocket())

    assert manager.active_connections == []


def _order_event(*stations: str, event: str = "order_created") -> dict:
    return {
        "event": event,
        "order": {
            "id": 1,
            "stations": sorted(set(stations)),
            "items": [{"dish_id": n, "station": s} for n, s in enumerate(stations)],
        },
    }


def _connect_with_role(manager: KitchenConnectionManager, ws: FakeWebSocket, role: str) -> None:
    asyncio.run(manager.connect(ws, role))


def test_broadcast_to_stations_filters_items_by_role():
    manager = KitchenConnectionManager()
    kitchen, bar, admin = FakeWebSocket(), FakeWebSocket(), FakeWebSocket()
    _connect_with_role(manager, kitchen, "kitchen")
    _connect_with_role(manager, bar, "bartender")
    _connect_with_role(manager, admin, "admin")

    asyncio.run(manager.broadcast_to_stations(_order_event("kitchen", "bar")))

    stations = {
        name: [i["station"] for i in json.loads(ws.sent[0])["order"]["items"]]
        for name, ws in {"kitchen": kitchen, "bar": bar, "admin": admin}.items()
    }
    assert stations == {"kitchen": ["kitchen"], "bar": ["bar"], "admin": ["kitchen", "bar"]}


def test_broadcast_to_stations_skips_stations_without_lines():
    manager = KitchenConnectionManager()
    kitchen, bar = FakeWebSocket(), FakeWebSocket()
    _connect_with_role(manager, kitchen, "kitchen")
    _connect_with_role(manager, bar, "bartender")

    asyncio.run(manager.broadcast_to_stations(_order_event("bar")))

    assert kitchen.sent == []
    assert len(bar.sent) == 1


def test_broadcast_to_stations_routes_status_events_by_order_stations():
    manager = KitchenConnectionManager()
    kitchen, bar = FakeWebSocket(), FakeWebSocket()
    _connect_with_role(manager, kitchen, "kitchen")
    _connect_with_role(manager, bar, "bartender")
    event = {"event": "order_status_changed", "order": {"id": 1, "stations": ["kitchen"]}}

    asyncio.run(manager.broadcast_to_stations(event))

    assert len(kitchen.sent) == 1
    assert bar.sent == []


def test_broadcast_to_stations_drops_broken_connections():
    manager = KitchenConnectionManager()
    broken = FakeWebSocket(RuntimeError("cerrado"))
    _connect_with_role(manager, broken, "admin")

    asyncio.run(manager.broadcast_to_stations(_order_event("kitchen")))

    assert manager.active_connections == []
