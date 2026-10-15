from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.models.model_order import Order
from app.repositories import dining_table_repository, dish_repository, order_repository
from app.schemas.schema_order import OrderCreate
from app.websocket.kitchen import kitchen_manager

VALID_TRANSITIONS = {
    "pending": {"in_kitchen", "cancelled"},
    "in_kitchen": {"served", "cancelled"},
    "served": {"paid", "cancelled"},
    "paid": set(),
    "cancelled": set(),
}

CLOSED_STATUSES = {"paid", "cancelled"}


def create_order(
    db: Session,
    data: OrderCreate,
    background_tasks: BackgroundTasks,
    waiter_id: int | None = None,
) -> Order:
    table = dining_table_repository.get_by_id(db, data.table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    total = 0
    order_items = []

    for item in data.items:
        dish = dish_repository.get_by_id(db, item.dish_id)

        if not dish or not dish.is_available:
            raise HTTPException(status_code=409, detail=f"Dish {item.dish_id} not available")

        unit_price = dish.price
        total += item.quantity * unit_price

        order_items.append({
            "dish_id": item.dish_id,
            "quantity": item.quantity,
            "unit_price": unit_price,
            "notes": item.notes,
        })

    order = order_repository.add_with_items(
        db,
        Order(table_id=data.table_id, waiter_id=waiter_id, total=total, status="pending"),
        order_items,
    )

    background_tasks.add_task(
        kitchen_manager.broadcast,
        {
            "event": "order_created",
            "order": {
                "id": order.id,
                "table_id": order.table_id,
                "table_number": table.number,
                "waiter_id": order.waiter_id,
                "status": order.status,
                "total": str(order.total),
                "items": [
                    {
                        "dish_id": item.dish_id,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                    }
                    for item in order.items
                ],
            },
        },
    )

    return order


def list_orders(
    db: Session,
    status: str | None = None,
    table_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Order]:
    return order_repository.list_orders(db, status, table_id, date_from, date_to, skip, limit)


def get_order(db: Session, order_id: int) -> Order:
    order = order_repository.get_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def update_order_status(
    db: Session, order_id: int, new_status: str, background_tasks: BackgroundTasks
) -> Order:
    order = get_order(db, order_id)

    if new_status == order.status:
        return order

    allowed = VALID_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change status from '{order.status}' to '{new_status}'",
        )

    order.status = new_status
    order_repository.save(db, order)

    table = dining_table_repository.get_by_id(db, order.table_id)
    background_tasks.add_task(
        kitchen_manager.broadcast,
        {
            "event": "order_status_changed",
            "order": {
                "id": order.id,
                "table_id": order.table_id,
                "table_number": table.number if table else None,
                "status": order.status,
                "total": str(order.total),
            },
        },
    )

    return order


def update_item(db: Session, order_id: int, item_id: int, changes: dict[str, bool | int]) -> Order:
    order = get_order(db, order_id)
    item = next((i for i in order.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Order item not found")
    if order.status in CLOSED_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change items of an order in status '{order.status}'",
        )
    quantities = {
        f"{field}_quantity": item.quantity if value else 0
        for field, value in changes.items()
        if field in ("prepared", "served")
    }
    quantities |= {field: value for field, value in changes.items() if field.endswith("_quantity")}
    for field, value in quantities.items():
        if value > item.quantity:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be greater than the quantity of the line ({item.quantity})",
            )
        setattr(item, field, value)
    return order_repository.save(db, order)
