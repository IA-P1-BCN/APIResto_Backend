from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.pagination import Page, PageParams, paginate
from app.models.model_dish import Dish
from app.repositories import dish_repository
from app.schemas.schema_dish import DishCreate, DishOut, DishUpdate
from app.services import category_service


def get_dish(db: Session, dish_id: int) -> Dish:
    """Return the dish or raise NotFoundError (404)."""
    dish = dish_repository.get_by_id(db, dish_id)
    if not dish:
        raise NotFoundError("Dish not found")
    return dish


def list_dishes(
    db: Session,
    params: PageParams,
    category_id: int | None = None,
    is_available: bool | None = None,
    max_price: Decimal | None = None,
) -> Page[DishOut]:
    stmt = dish_repository.filtered_query(category_id, is_available, max_price)
    return paginate(db, stmt, params, DishOut)


def create_dish(db: Session, data: DishCreate) -> Dish:
    category_service.get_category(db, data.category_id)
    return dish_repository.add(db, Dish(**data.model_dump()))


def update_dish(db: Session, dish_id: int, data: DishUpdate) -> Dish:
    dish = get_dish(db, dish_id)

    if data.category_id is not None:
        category_service.get_category(db, data.category_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dish, field, value)

    return dish_repository.save(db, dish)


def delete_dish(db: Session, dish_id: int) -> None:
    dish = get_dish(db, dish_id)

    if dish_repository.is_used_in_orders(db, dish_id):
        raise ConflictError(
            "Dish is used in orders and cannot be deleted. "
            "Mark it as unavailable instead"
        )

    dish_repository.delete(db, dish)
