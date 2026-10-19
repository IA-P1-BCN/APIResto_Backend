from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import MENU_READ, MENU_WRITE, require_role
from app.database import get_db
from app.schemas.schema_category import CategoryCreate, CategoryOut, CategoryUpdate
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])

DbSession = Annotated[Session, Depends(get_db)]

READ = [Depends(require_role(*MENU_READ))]
WRITE = [Depends(require_role(*MENU_WRITE))]


@router.post("/", response_model=CategoryOut, status_code=201, dependencies=WRITE)
def create_category(category: CategoryCreate, db: DbSession):
    return category_service.create_category(db, category)


@router.get("/", response_model=list[CategoryOut], dependencies=READ)
def list_categories(db: DbSession):
    return category_service.list_categories(db)


@router.get("/{category_id}", response_model=CategoryOut, dependencies=READ)
def get_category(category_id: int, db: DbSession):
    return category_service.get_category(db, category_id)


@router.put("/{category_id}", response_model=CategoryOut, dependencies=WRITE)
def update_category(category_id: int, data: CategoryUpdate, db: DbSession):
    return category_service.update_category(db, category_id, data)


@router.delete("/{category_id}", status_code=204, dependencies=WRITE)
def delete_category(category_id: int, db: DbSession):
    category_service.delete_category(db, category_id)
