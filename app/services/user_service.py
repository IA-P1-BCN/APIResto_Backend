from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.model_user import Role, User
from app.repositories import user_repository
from app.schemas.schema_user import UserCreate, UserRegister, UserUpdate
<<<<<<< HEAD


def normalize_email(email: str) -> str:
    """R-01: el email se guarda en minúsculas y sin espacios sobrantes."""
    return email.strip().lower()
=======
>>>>>>> 02bdfd40f4d4fdae3ccf0535de9af97263a63fd6


def normalize_email(email: str) -> str:
    """R-01: el email se guarda en minúsculas y sin espacios sobrantes."""
    return email.strip().lower()


def get_user(db: Session, user_id: int, include_deleted: bool = False) -> User:
    user = user_repository.get_by_id(db, user_id)
    if not user or (user.deleted_at is not None and not include_deleted):
        raise HTTPException(status_code=404, detail="User not found")
    return user


def list_users(
    db: Session, skip: int = 0, limit: int = 100, include_deleted: bool = False
) -> list[User]:
    return user_repository.list_users(db, skip=skip, limit=limit, include_deleted=include_deleted)


<<<<<<< HEAD
def create_user(db: Session, data: UserCreate) -> User:
=======
def create_user(db: Session, data: UserCreate, actor: User | None = None) -> User:
>>>>>>> 02bdfd40f4d4fdae3ccf0535de9af97263a63fd6
    email = normalize_email(data.email)
    if user_repository.get_by_email(db, email):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=data.name,
        email=email,
        password_hash=hash_password(data.password),
        phone=data.phone,
        role=data.role.value,
        created_by=actor.id if actor else None,
        updated_by=actor.id if actor else None,
    )
    return user_repository.add(db, user)


def register_user(db: Session, data: UserRegister) -> User:
    """Auto-registro público: crea siempre un `customer`, ignora el rol (R-03)."""
    email = normalize_email(data.email)
    if user_repository.get_by_email(db, email):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=data.name,
        email=email,
        password_hash=hash_password(data.password),
        phone=data.phone,
        role=Role.customer.value,
    )
    return user_repository.add(db, user)


<<<<<<< HEAD
def update_user(db: Session, user_id: int, data: UserUpdate) -> User:
=======
def update_user(db: Session, user_id: int, data: UserUpdate, actor: User) -> User:
>>>>>>> 02bdfd40f4d4fdae3ccf0535de9af97263a63fd6
    user = get_user(db, user_id)
    fields = data.model_dump(mode="json", exclude_unset=True)

    if "email" in fields:
        fields["email"] = normalize_email(fields["email"])
        if fields["email"] != user.email and user_repository.get_by_email(db, fields["email"]):
            raise HTTPException(status_code=409, detail="Email already registered")

    for field, value in fields.items():
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
    if not user or not user.is_active or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
