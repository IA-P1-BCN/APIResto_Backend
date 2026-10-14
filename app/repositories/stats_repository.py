from datetime import date, datetime, time, timedelta

from sqlalchemy import Row, Select, func, select
from sqlalchemy.orm import Session

from app.models.model_dish import Dish
from app.models.model_order import Order
from app.models.model_order_item import OrderItem

SALE_STATUSES = ("served", "paid")


def _sales_filter(
    stmt: Select, date_from: date | None, date_to: date | None
) -> Select:
    """Solo pedidos que son venta y, si se indican, dentro del rango de fechas."""
    stmt = stmt.where(Order.status.in_(SALE_STATUSES))
    if date_from is not None:
        stmt = stmt.where(Order.created_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        next_day = datetime.combine(date_to + timedelta(days=1), time.min)
        stmt = stmt.where(Order.created_at < next_day)
    return stmt


def sales_by_day(
    db: Session, date_from: date | None, date_to: date | None
) -> list[Row]:
    """Filas (día, nº de pedidos, suma de totales) de los pedidos que son venta."""
    day = func.date(Order.created_at)
    stmt = _sales_filter(
        select(day, func.count(Order.id), func.sum(Order.total)),
        date_from,
        date_to,
    )
    return list(db.execute(stmt.group_by(day).order_by(day)).all())


def top_dishes_rows(
    db: Session, date_from: date | None, date_to: date | None, limit: int
) -> list[Row]:
    """Filas (id, nombre, unidades, ingresos) por plato. Empate: ingresos y luego id."""
    quantity = func.sum(OrderItem.quantity)
    revenue = func.sum(OrderItem.quantity * OrderItem.unit_price)
    stmt = _sales_filter(
        select(Dish.id, Dish.name, quantity, revenue)
        .join(OrderItem, OrderItem.dish_id == Dish.id)
        .join(Order, Order.id == OrderItem.order_id),
        date_from,
        date_to,
    )
    stmt = (
        stmt.group_by(Dish.id, Dish.name)
        .order_by(quantity.desc(), revenue.desc(), Dish.id)
        .limit(limit)
    )
    return list(db.execute(stmt).all())
