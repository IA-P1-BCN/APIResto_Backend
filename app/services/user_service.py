from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.model_user import Role, User
from app.repositories import user_repository
from app.schemas.schema_user import UserCreate, UserRegister, UserUpdate


def normalize_email(email: str) -> str:
    """R-01: el email se guarda en minúsculas y sin espacios sobrantes."""
    return email.strip().lower()


def get_user(db: Session, user_id: int) -> User:
    user = user_repository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    return user_repository.list_users(db, skip=skip, limit=limit)


def create_user(db: Session, data: UserCreate) -> User:
    email = normalize_email(data.email)
    if user_repository.get_by_email(db, email):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=data.name,
        email=email,
        password_hash=hash_password(data.password),
        phone=data.phone,
        role=data.role.value,
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


def update_user(db: Session, user_id: int, data: UserUpdate) -> User:
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

    return user_repository.save(db, user)


def deactivate_user(db: Session, user_id: int) -> User:
    user = get_user(db, user_id)
    user.is_active = False
    return user_repository.save(db, user)


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Return the active user whose credentials match, or None."""
    user = user_repository.get_by_email(db, email)
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user
