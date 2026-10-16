"""
Gestor de conexiones WebSocket para la cocina.

Mantiene una lista de clientes conectados y permite enviar
mensajes a todos ellos cuando hay un evento nuevo.
"""

import json
import logging

from fastapi import WebSocket

from app.core.stations import station_for_role

logger = logging.getLogger(__name__)


class KitchenConnectionManager:
    """Administra las conexiones WebSocket activas de la cocina."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.roles: dict[WebSocket, str | None] = {}

    async def connect(self, websocket: WebSocket, role: str | None = None):
        """Acepta una nueva conexión de un cliente de cocina o barra."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.roles[websocket] = role
        logger.info(f"Cocinero conectado. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Elimina una conexión cuando el cliente se desconecta."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.roles.pop(websocket, None)
            logger.info(f"Cocinero desconectado. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Envía un mensaje a TODOS los cocineros conectados."""
        json_message = json.dumps(message)

        for connection in list(self.active_connections):
            try:
                await connection.send_text(json_message)
            except (ConnectionError, RuntimeError):
                self.disconnect(connection)

    async def broadcast_to_stations(self, message: dict):
        """Envía a cada conexión solo lo de su estación (R-14).

        `order.stations` lista las estaciones del pedido; `order.items`, si existe, se
        recorta a la estación de la conexión. Sin estación (admin) recibe todo.
        """
        order = message["order"]
        for connection in list(self.active_connections):
            station = station_for_role(self.roles.get(connection) or "")
            payload = message
            if station is not None:
                if station.value not in order["stations"]:
                    continue
                if "items" in order:
                    items = [i for i in order["items"] if i["station"] == station.value]
                    payload = {**message, "order": {**order, "items": items}}
            try:
                await connection.send_text(json.dumps(payload))
            except (ConnectionError, RuntimeError):
                self.disconnect(connection)


kitchen_manager = KitchenConnectionManager()
