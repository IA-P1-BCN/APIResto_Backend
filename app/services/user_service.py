from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.model_user import User
from app.repositories import user_repository
from app.schemas.schema_user import UserCreate, UserUpdate


def get_user(db: Session, user_id: int, include_deleted: bool = False) -> User:
    user = user_repository.get_by_id(db, user_id)
    if not user or (user.deleted_at is not None and not include_deleted):
        raise HTTPException(status_code=404, detail="User not found")
    return user


def list_users(
    db: Session, skip: int = 0, limit: int = 100, include_deleted: bool = False
) -> list[User]:
    return user_repository.list_users(db, skip=skip, limit=limit, include_deleted=include_deleted)


def create_user(db: Session, data: UserCreate, actor: User | None = None) -> User:
    if user_repository.get_by_email(db, data.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        phone=data.phone,
        role=data.role.value,
        created_by=actor.id if actor else None,
        updated_by=actor.id if actor else None,
    )
    return user_repository.add(db, user)


def update_user(db: Session, user_id: int, data: UserUpdate, actor: User) -> User:
    user = get_user(db, user_id)

    if (
        data.email
        and data.email != user.email
        and user_repository.get_by_email(db, data.email)
    ):
        raise HTTPException(status_code=409, detail="Email already registered")

    for field, value in data.model_dump(mode="json", exclude_unset=True).items():
        if field == "password":
            user.password_hash = hash_password(value)
        else:
            setattr(user, field, value)

    user.updated_by = actor.id
    return user_repository.save(db, user)


def _ensure_not_self(user: User, actor: User) -> None:
    if user.id == actor.id:
        raise HTTPException(status_code=403, detail="Admins cannot deactivate or delete themselves")


def deactivate_user(db: Session, user_id: int, actor: User) -> User:
    user = get_user(db, user_id)
    _ensure_not_self(user, actor)
    user.is_active = False
    user.updated_by = actor.id
    return user_repository.save(db, user)


def delete_user(db: Session, user_id: int, actor: User) -> User:
    user = get_user(db, user_id)
    _ensure_not_self(user, actor)
    user.is_active = False
    user.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    user.updated_by = actor.id
    return user_repository.save(db, user)


def restore_user(db: Session, user_id: int, actor: User) -> User:
    user = get_user(db, user_id, include_deleted=True)
    if user.deleted_at is None:
        raise HTTPException(status_code=409, detail="User is not deleted")
    user.deleted_at = None
    user.is_active = True
    user.updated_by = actor.id
    return user_repository.save(db, user)


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Return the active user whose credentials match, or None."""
    user = user_repository.get_by_email(db, email)
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user
