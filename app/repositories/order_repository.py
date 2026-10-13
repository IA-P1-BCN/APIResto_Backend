from sqlalchemy.orm import Session

from app.models.model_order import Order
from app.models.model_order_item import OrderItem


def get_by_id(db: Session, order_id: int) -> Order | None:
    return db.query(Order).filter(Order.id == order_id).first()


def list_orders(
    db: Session,
    status: str | None = None,
    table_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Order]:
    query = db.query(Order)

    if status:
        query = query.filter(Order.status == status)
    if table_id:
        query = query.filter(Order.table_id == table_id)
    if date_from:
        query = query.filter(Order.created_at >= date_from)
    if date_to:
        query = query.filter(Order.created_at <= date_to)

    return query.offset(skip).limit(limit).all()


def add_with_items(db: Session, order: Order, items: list[dict]) -> Order:
    db.add(order)
    db.flush()

    for item_data in items:
        db.add(OrderItem(order_id=order.id, **item_data))

    db.commit()
    db.refresh(order)
    return order


def save(db: Session, order: Order) -> Order:
    db.commit()
    db.refresh(order)
    return order
