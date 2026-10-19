from datetime import datetime

from sqlalchemy.orm import Session

from app.models.model_revoked_token import RevokedToken


def is_revoked(db: Session, jti: str) -> bool:
    return db.query(RevokedToken).filter(RevokedToken.jti == jti).first() is not None


def add(db: Session, jti: str, expires_at: datetime) -> None:
    entry = RevokedToken(jti=jti, expires_at=expires_at)
    db.add(entry)
    db.commit()
