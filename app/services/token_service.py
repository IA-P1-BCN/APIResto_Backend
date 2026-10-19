import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.model_user import User
from app.repositories import (
    refresh_token_repository,
    revoked_token_repository,
    user_repository,
)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_token_pair(db: Session, user: User) -> dict:
    """Emite un AccessToken JWT + RefreshToken (R-05)."""
    access_token = create_access_token(user.id, user.role)
    refresh_plain = create_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    refresh_token_repository.add(db, user.id, _hash(refresh_plain), expires_at)
    return {"access_token": access_token, "refresh_token": refresh_plain, "token_type": "bearer"}


def refresh(db: Session, refresh_plain: str) -> dict:
    """Rota el RefreshToken: emite par nuevo y revoca el usado (R-06)."""
    rt = refresh_token_repository.get_by_hash(db, _hash(refresh_plain))
    if not rt or rt.revoked_at or rt.expires_at < datetime.now(UTC):
        raise ValueError("refresh token inválido o caducado")

    user = user_repository.get_by_id(db, rt.user_id)
    if not user or not user.is_active:
        raise ValueError("cuenta desactivada")

    refresh_token_repository.revoke(db, rt)

    access_token = create_access_token(user.id, user.role)
    new_refresh_plain = create_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    refresh_token_repository.add(db, user.id, _hash(new_refresh_plain), expires_at)
    return {"access_token": access_token, "refresh_token": new_refresh_plain, "token_type": "bearer"}


def logout(db: Session, refresh_plain: str, access_jti: str, access_expires: datetime) -> None:
    """Cierra sesión: revoca el RefreshToken y añade el jti del AccessToken a RevokedToken (R-07)."""
    rt = refresh_token_repository.get_by_hash(db, _hash(refresh_plain))
    if rt:
        refresh_token_repository.revoke(db, rt)
    revoked_token_repository.add(db, access_jti, access_expires)
