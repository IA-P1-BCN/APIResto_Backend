from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import USERS, require_role
from app.database import get_db
from app.schemas.schema_user import UserCreate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_role(*USERS))],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/", response_model=UserOut, status_code=201)
def create_user(user: UserCreate, db: DbSession):
    return user_service.create_user(db, user)


@router.get("/", response_model=list[UserOut])
def list_users(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    return user_service.list_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: DbSession):
    return user_service.get_user(db, user_id)


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db: DbSession):
    return user_service.update_user(db, user_id, data)


@router.patch("/{user_id}/deactivate", response_model=UserOut)
def deactivate(user_id: int, db: DbSession):
    return user_service.deactivate_user(db, user_id)