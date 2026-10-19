from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.pagination import Page, PageParamsDep
from app.core.permissions import MENU_READ, MENU_WRITE, require_role
from app.database import get_db
from app.schemas.schema_dish import DishCreate, DishOut, DishUpdate
from app.services import dish_service

router = APIRouter(prefix="/dishes", tags=["dishes"])

DbSession = Annotated[Session, Depends(get_db)]

READ = [Depends(require_role(*MENU_READ))]
WRITE = [Depends(require_role(*MENU_WRITE))]


@router.post("/", response_model=DishOut, status_code=201, dependencies=WRITE)
def create_dish(dish: DishCreate, db: DbSession):
    return dish_service.create_dish(db, dish)


@router.get("/", response_model=Page[DishOut], dependencies=READ)
def list_dishes(
    db: DbSession,
    params: PageParamsDep,
    category_id: int | None = None,
    is_available: bool | None = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
):
    return dish_service.list_dishes(
        db,
        params,
        category_id=category_id,
        is_available=is_available,
        max_price=max_price,
    )


@router.get("/{dish_id}", response_model=DishOut, dependencies=READ)
def get_dish(dish_id: int, db: DbSession):
    return dish_service.get_dish(db, dish_id)


@router.put("/{dish_id}", response_model=DishOut, dependencies=WRITE)
def update_dish(dish_id: int, data: DishUpdate, db: DbSession):
    return dish_service.update_dish(db, dish_id, data)


@router.delete("/{dish_id}", status_code=204, dependencies=WRITE)
def delete_dish(dish_id: int, db: DbSession):
    dish_service.delete_dish(db, dish_id)
