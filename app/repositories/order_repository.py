from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.model_category import Category, Station
from app.models.model_dish import Dish
from app.models.model_order import Order
from app.models.model_order_item import OrderItem


def exists_for_table(db: Session, table_id: int) -> bool:
    return (
        db.scalar(select(Order.id).where(Order.table_id == table_id).limit(1)) is not None
    )


WITH_STATIONS = (selectinload(Order.items).joinedload(OrderItem.dish).joinedload(Dish.category),)


def _with_station_lines(station: Station):
    return Order.id.in_(
        select(OrderItem.order_id)
        .join(Dish, Dish.id == OrderItem.dish_id)
        .join(Category, Category.id == Dish.category_id)
        .where(Category.station == station.value)
    )


def get_by_id(db: Session, order_id: int, station: Station | None = None) -> Order | None:
    query = db.query(Order).options(*WITH_STATIONS).filter(Order.id == order_id)
    if station:
        query = query.filter(_with_station_lines(station))
    return query.first()


def list_orders(
    db: Session,
    status: str | None = None,
    table_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    skip: int = 0,
    limit: int = 100,
    station: Station | None = None,
) -> list[Order]:
    query = db.query(Order).options(*WITH_STATIONS)

    if station:
        query = query.filter(_with_station_lines(station))

    if status:
        query = query.filter(Order.status == status)
    if table_id:
        query = query.filter(Order.table_id == table_id)
    if date_from:
        query = query.filter(Order.created_at >= date_from)
    if date_to:
        query = query.filter(Order.created_at <= date_to)

    return query.order_by(Order.id).offset(skip).limit(limit).all()


def list_for_export(
    db: Session,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[Order]:
    stmt = select(Order).options(selectinload(Order.items), selectinload(Order.invoice))
    if status is not None:
        stmt = stmt.where(Order.status == status)
    if date_from is not None:
        stmt = stmt.where(Order.created_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        next_day = datetime.combine(date_to + timedelta(days=1), time.min)
        stmt = stmt.where(Order.created_at < next_day)
    return list(db.scalars(stmt.order_by(Order.id)).all())


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
