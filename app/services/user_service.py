import logging
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    UnprocessableError,
)
from app.core.pagination import Page, PageParams, paginate
from app.core.security import hash_password, verify_password
from app.models.model_user import Role, User
from app.repositories import user_repository
from app.schemas.schema_user import (
    PasswordChange,
    UserCreate,
    UserOut,
    UserProfileUpdate,
    UserRegister,
    UserUpdate,
)

logger = logging.getLogger(__name__)


def normalize_email(email: str) -> str:
    """R-01: el email se guarda en minúsculas y sin espacios sobrantes."""
    return email.strip().lower()


def get_user(db: Session, user_id: int, include_deleted: bool = False) -> User:
    user = user_repository.get_by_id(db, user_id)
    if not user or (user.deleted_at is not None and not include_deleted):
        raise HTTPException(status_code=404, detail="User not found")
    return user


def list_users(
    db: Session,
    params: PageParams,
    role: Role | None = None,
    is_active: bool | None = None,
    q: str | None = None,
    include_deleted: bool = False,
) -> Page[UserOut]:
    """Listado paginado con filtros combinables (HU-24). `q` vacío no filtra."""
    search = q.strip() if q else None
    stmt = user_repository.filtered_query(
        role=role, is_active=is_active, search=search, include_deleted=include_deleted
    )
    return paginate(db, stmt, params, UserOut)


def create_user(db: Session, data: UserCreate, actor: User | None = None) -> User:
    """Alta por un admin: nace con el email verificado (R-15, decisión C)."""
    email = normalize_email(data.email)
    if user_repository.get_by_email(db, email):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=data.name,
        email=email,
        password_hash=hash_password(data.password),
        phone=data.phone,
        role=data.role.value,
        email_verified=True,
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


def update_user(db: Session, user_id: int, data: UserUpdate, actor: User) -> User:
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


def update_profile(db: Session, user: User, data: UserProfileUpdate) -> User:
    """Edita el propio perfil con los campos enviados; el email debe ser único (R-01)."""
    fields = data.model_dump(exclude_unset=True)

    if "email" in fields:
        fields["email"] = normalize_email(fields["email"])
        if fields["email"] != user.email:
            existing = user_repository.get_by_email(db, fields["email"])
            if existing and existing.id != user.id:
                logger.warning(
                    "Profile update rejected",
                    extra={"user_id": user.id, "code": "conflict"},
                )
                raise ConflictError("Email already registered")

    for field, value in fields.items():
        setattr(user, field, value)

    user.updated_by = user.id
    user = user_repository.save(db, user)
    logger.info("Profile updated", extra={"user_id": user.id, "fields": sorted(fields)})
    return user


def change_password(db: Session, user: User, data: PasswordChange) -> None:
    """Cambia la propia contraseña tras verificar la actual (R-02)."""
    if not user.password_hash:
        _reject_password_change(user, "password_not_set")
        raise AppError("Password not set for this account", code="password_not_set")
    if not verify_password(data.current_password, user.password_hash):
        _reject_password_change(user, "invalid_current_password")
        raise ForbiddenError("Current password is incorrect", code="invalid_current_password")
    if verify_password(data.new_password, user.password_hash):
        _reject_password_change(user, "same_password")
        raise UnprocessableError(
            "New password must be different from the current one", code="same_password"
        )

    user.password_hash = hash_password(data.new_password)
    user.updated_by = user.id
    user_repository.save(db, user)
    logger.info("Password changed", extra={"user_id": user.id})


def _reject_password_change(user: User, code: str) -> None:
    logger.warning("Password change rejected", extra={"user_id": user.id, "code": code})
