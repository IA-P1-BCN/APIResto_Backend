from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.model_user import Role, User

LIKE_ESCAPE_CHAR = "\\"


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_by_email(db: Session, email: str) -> User | None:
    normalized = email.strip().lower()
    return db.query(User).filter(func.lower(User.email) == normalized).first()


def _like_pattern(text: str) -> str:
    """Patrón LIKE de coincidencia parcial que trata `%` y `_` como texto literal."""
    escaped = (
        text.replace(LIKE_ESCAPE_CHAR, LIKE_ESCAPE_CHAR * 2)
        .replace("%", LIKE_ESCAPE_CHAR + "%")
        .replace("_", LIKE_ESCAPE_CHAR + "_")
    )
    return f"%{escaped.lower()}%"


def filtered_query(
    role: Role | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    include_deleted: bool = False,
) -> Select:
    """Consulta de usuarios filtrada y ordenada por `id` (HU-24)."""
    stmt = select(User)

    if not include_deleted:
        stmt = stmt.where(User.deleted_at.is_(None))
    if role is not None:
        stmt = stmt.where(User.role == role.value)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if search:
        pattern = _like_pattern(search)
        stmt = stmt.where(
            or_(
                func.lower(User.name).like(pattern, escape=LIKE_ESCAPE_CHAR),
                func.lower(User.email).like(pattern, escape=LIKE_ESCAPE_CHAR),
            )
        )

    return stmt.order_by(User.id)


def add(db: Session, user: User) -> User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def save(db: Session, user: User) -> User:
    db.commit()
    db.refresh(user)
    return user
