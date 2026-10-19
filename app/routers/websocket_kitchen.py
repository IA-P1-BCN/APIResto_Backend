"""
Endpoint WebSocket para la cocina.

Los cocineros se conectan a /ws/kitchen y reciben
notificaciones en tiempo real cuando se crean pedidos
o cambian de estado.

El token se pasa como parámetro de query: /ws/kitchen?token=<token>
Solo pueden conectarse usuarios activos con rol admin o kitchen (HU-05).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.permissions import BARTENDER, KITCHEN
from app.core.security import decode_access_token
from app.database import get_db
from app.repositories import user_repository
from app.websocket.kitchen import kitchen_manager

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_ROLES = {role.value for role in (*KITCHEN, *BARTENDER)}


@router.websocket("/ws/kitchen")
async def kitchen_websocket(
    websocket: WebSocket,
    db: Annotated[Session, Depends(get_db)],
    token: str | None = None,
):
    """
    Conexión WebSocket para la vista de cocina.

    El cliente se conecta y permanece escuchando.
    El servidor envía eventos cuando hay pedidos nuevos
    o cambios de estado.

    Requiere token de autenticación como parámetro de query:
    ws://localhost:8000/ws/kitchen?token=<token>

    Cierra con 1008 si falta el token, no es válido o el usuario no existe,
    está desactivado o no tiene rol admin o kitchen.
    """
    payload = decode_access_token(token) if token else None
    user = user_repository.get_by_id(db, int(payload["sub"])) if payload is not None else None
    allowed = user is not None and user.is_active and user.role in ALLOWED_ROLES
    db.close()
    if not allowed:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await kitchen_manager.connect(websocket, user.role)

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Mensaje de cocina: {data}")

    except WebSocketDisconnect:
        kitchen_manager.disconnect(websocket)
