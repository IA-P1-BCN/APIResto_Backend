from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.model_refresh_token import RefreshToken


def add(db: Session, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
    rt = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


def get_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
    return db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()


def revoke(db: Session, rt: RefreshToken) -> None:
    rt.revoked_at = datetime.now(UTC)
    db.commit()
