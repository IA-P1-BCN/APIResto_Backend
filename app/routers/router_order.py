from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import BARTENDER, KITCHEN, ORDERS, require_role
from app.core.stations import station_for_role
from app.database import get_db
from app.models.model_user import User
from app.schemas.schema_order import (
    OrderCreate,
    OrderItemUpdate,
    OrderOut,
    OrderStatusUpdate,
)
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])

Waiter = Annotated[User, Depends(require_role(*ORDERS))]
StaffUser = Annotated[User, Depends(require_role(*ORDERS, *KITCHEN, *BARTENDER))]

@router.post("/", response_model=OrderOut, status_code=201)
def create_order(
    order: OrderCreate,
    user: Waiter,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_service.create_order(db, order, background_tasks, waiter_id=user.id)

@router.get("/", response_model=list[OrderOut])
def list_orders(
    user: StaffUser,
    status: str | None = None,
    table_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)  # noqa: B008
):
    return order_service.list_orders(
        db, status, table_id, date_from, date_to, skip, limit, station_for_role(user.role)
    )

@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, user: StaffUser, db: Session = Depends(get_db)):  # noqa: B008
    return order_service.get_order_view(db, order_id, station_for_role(user.role))


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    body: OrderStatusUpdate,
    user: StaffUser,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),  # noqa: B008
):
    return order_service.update_order_status(
        db, order_id, body.status, background_tasks, station_for_role(user.role)
    )


PREPARE_ROLES = {role.value for role in (*KITCHEN, *BARTENDER)}
SERVE_ROLES = {role.value for role in ORDERS}
ITEM_FIELD_ROLES = {
    "prepared": PREPARE_ROLES,
    "prepared_quantity": PREPARE_ROLES,
    "served": SERVE_ROLES,
    "served_quantity": SERVE_ROLES,
}


@router.patch("/{order_id}/items/{item_id}", response_model=OrderOut)
def update_order_item(
    order_id: int,
    item_id: int,
    body: OrderItemUpdate,
    user: StaffUser,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Marca cuántas unidades de una línea están preparadas (cocina) o servidas (sala).

    `prepared_quantity` y `served_quantity` van de 0 a la cantidad de la línea.
    `prepared` y `served` (true/false) marcan o desmarcan todas las unidades.
    `prepared` / `prepared_quantity`: admin, kitchen, bartender.
    `served` / `served_quantity`: admin, waiter.
    kitchen y bartender solo sobre líneas de su estación (R-14); otra estación → 403.
    """
    changes = body.model_dump(exclude_none=True)
    for field in changes:
        if user.role not in ITEM_FIELD_ROLES[field]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    return order_service.update_item(db, order_id, item_id, changes, station_for_role(user.role))
