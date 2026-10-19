from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.model_email_verification_token import EmailVerificationToken


def add(db: Session, token: EmailVerificationToken) -> EmailVerificationToken:
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_by_hash_for_update(db: Session, token_hash: str) -> EmailVerificationToken | None:
    """Token bloqueando su fila (FOR UPDATE en Postgres) hasta el commit.

    Así dos peticiones con el mismo token no pueden comprobar a la vez que está sin usar.
    """
    return db.execute(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.token_hash == token_hash)
        .with_for_update()
    ).scalar_one_or_none()


def list_pending_for_user(db: Session, user_id: int) -> list[EmailVerificationToken]:
    return (
        db.query(EmailVerificationToken)
        .filter(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.used_at.is_(None),
        )
        .all()
    )


def get_latest_for_user(db: Session, user_id: int) -> EmailVerificationToken | None:
    """Último token emitido para el usuario (usado o no), o None si no tiene ninguno."""
    return (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.user_id == user_id)
        .order_by(EmailVerificationToken.created_at.desc(), EmailVerificationToken.id.desc())
        .first()
    )
