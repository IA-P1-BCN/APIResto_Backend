from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.model_password_reset_token import PasswordResetToken
from app.models.model_user import User


def add(db: Session, token: PasswordResetToken) -> PasswordResetToken:
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def add_invited_user(db: Session, user: User, token: PasswordResetToken) -> User:
    """Guarda el usuario y su token en una sola transacción: o los dos o ninguno."""
    db.add(user)
    db.flush()
    token.user_id = user.id
    db.add(token)
    db.commit()
    db.refresh(user)
    return user


def get_by_hash_for_update(db: Session, token_hash: str) -> PasswordResetToken | None:
    """Token bloqueando su fila (FOR UPDATE en Postgres) hasta el commit.

    Así dos peticiones con el mismo token no pueden comprobar a la vez que está sin usar.
    """
    return db.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .with_for_update()
    ).scalar_one_or_none()


def list_pending_for_user(db: Session, user_id: int) -> list[PasswordResetToken]:
    return (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
        .all()
    )


def get_latest_for_user(db: Session, user_id: int) -> PasswordResetToken | None:
    """Último token emitido para el usuario (usado o no), o None si no tiene ninguno."""
    return (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user_id)
        .order_by(PasswordResetToken.created_at.desc(), PasswordResetToken.id.desc())
        .first()
    )
