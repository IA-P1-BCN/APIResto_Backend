from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.text_search import normalize_text, normalized_column
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
    return f"%{normalize_text(escaped)}%"


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
                normalized_column(User.name).like(pattern, escape=LIKE_ESCAPE_CHAR),
                normalized_column(User.email).like(pattern, escape=LIKE_ESCAPE_CHAR),
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


def get_by_id_for_update(db: Session, user_id: int) -> User | None:
    """Usuario leído de nuevo de la BD y con su fila bloqueada (FOR UPDATE en Postgres) hasta el commit.

    Así dos peticiones con el mismo código de recuperación no pueden gastarlo las dos (HU-37).
    """
    return db.execute(
        select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
    ).scalar_one_or_none()
