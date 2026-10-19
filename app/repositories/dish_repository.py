from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.model_dish import Dish
from app.models.model_order_item import OrderItem


def get_by_id(db: Session, dish_id: int) -> Dish | None:
    return db.query(Dish).filter(Dish.id == dish_id).first()


def filtered_query(
    category_id: int | None = None,
    is_available: bool | None = None,
    max_price: Decimal | None = None,
) -> Select:
    stmt = select(Dish)

    if category_id is not None:
        stmt = stmt.where(Dish.category_id == category_id)
    if is_available is not None:
        stmt = stmt.where(Dish.is_available == is_available)
    if max_price is not None:
        stmt = stmt.where(Dish.price <= max_price)

    return stmt.order_by(Dish.id)


def is_used_in_orders(db: Session, dish_id: int) -> bool:
    return bool(
        db.scalar(select(OrderItem.id).where(OrderItem.dish_id == dish_id).limit(1))
    )


def add(db: Session, dish: Dish) -> Dish:
    db.add(dish)
    db.commit()
    db.refresh(dish)
    return dish


def save(db: Session, dish: Dish) -> Dish:
    db.commit()
    db.refresh(dish)
    return dish


def delete(db: Session, dish: Dish) -> None:
    db.delete(dish)
    db.commit()
