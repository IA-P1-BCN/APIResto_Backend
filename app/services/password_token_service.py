"""Invitación por email para que el usuario cree su propia contraseña (HU-52).

Reglas (R-09): el token es de un solo uso y caduca a las PASSWORD_TOKEN_EXPIRE_HOURS
horas. Solo se guarda su SHA-256; el valor en claro va únicamente en el email y nunca
se registra en el log.
"""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from html import escape

from fastapi import status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import AppError, ConflictError
from app.core.security import hash_password
from app.models.model_password_reset_token import PasswordResetToken
from app.models.model_user import User
from app.repositories import password_reset_token_repository, user_repository
from app.schemas.schema_password_token import SetPasswordRequest, UserInvite
from app.services.user_service import normalize_email

logger = logging.getLogger(__name__)

SET_PASSWORD_PATH = "/crear-contrasena"
TOKEN_BYTES = 32
INVITATION_SUBJECT = "Crea tu contraseña de APIResto"


class TokenGoneError(AppError):
    """El token existió pero ya no sirve: usado o caducado (410)."""

    status_code = status.HTTP_410_GONE
    default_code = "token_gone"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_token() -> tuple[str, PasswordResetToken]:
    """Valor en claro y registro del token. Creación y caducidad salen del mismo reloj."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    now = _now()
    record = PasswordResetToken(
        token_hash=hash_token(token),
        created_at=now,
        expires_at=now + timedelta(hours=settings.PASSWORD_TOKEN_EXPIRE_HOURS),
    )
    return token, record


def issue_token(db: Session, user: User) -> str:
    """Crea un `PasswordResetToken` para el usuario y devuelve el valor en claro."""
    token, record = _new_token()
    record.user_id = user.id
    password_reset_token_repository.add(db, record)
    return token


def invite_user(db: Session, data: UserInvite, actor: User) -> tuple[User, str]:
    """Crea el usuario sin contraseña y su token en una sola transacción. Email repetido → 409 (R-01)."""
    email = normalize_email(data.email)
    if user_repository.get_by_email(db, email):
        logger.warning("Invitation rejected", extra={"code": "conflict"})
        raise ConflictError("Email already registered")

    token, record = _new_token()
    user = password_reset_token_repository.add_invited_user(
        db,
        User(
            name=data.name,
            email=email,
            password_hash=None,
            phone=data.phone,
            role=data.role.value,
            created_by=actor.id,
            updated_by=actor.id,
        ),
        record,
    )
    logger.info("User invited", extra={"user_id": user.id, "role": user.role})
    return user, token


def set_password_link(token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}{SET_PASSWORD_PATH}?token={token}"


def invitation_email(user: User, token: str) -> tuple[str, str, str]:
    """(to, subject, html) del email con el enlace para crear la contraseña."""
    link = escape(set_password_link(token), quote=True)
    hours = settings.PASSWORD_TOKEN_EXPIRE_HOURS
    html = (
        f"<p>Hola {escape(user.name)}:</p>"
        "<p>El restaurante te ha creado una cuenta en APIResto. "
        "Para empezar a usarla, elige tu contraseña:</p>"
        f'<p><a href="{link}">Crear mi contraseña</a></p>'
        f"<p>El enlace caduca en {hours} horas y solo se puede usar una vez. "
        "Si caduca, pide otro al restaurante.</p>"
        "<p>APIResto</p>"
    )
    return user.email, INVITATION_SUBJECT, html


def _invalid_token() -> AppError:
    logger.warning("Set password rejected", extra={"code": "invalid_token"})
    return AppError("Invalid token", code="invalid_token")


def _gone(detail: str, code: str, user_id: int) -> TokenGoneError:
    logger.warning("Set password rejected", extra={"user_id": user_id, "code": code})
    return TokenGoneError(detail, code=code)


def set_password(db: Session, data: SetPasswordRequest) -> None:
    """Fija la contraseña con el token y marca como usados todos los pendientes del usuario."""
    record = password_reset_token_repository.get_by_hash_for_update(db, hash_token(data.token))
    if record is None:
        raise _invalid_token()
    if record.used_at is not None:
        raise _gone("Token already used", "token_used", record.user_id)
    if record.expires_at <= _now():
        raise _gone("Token expired", "token_expired", record.user_id)

    user = user_repository.get_by_id(db, record.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise _invalid_token()

    now = _now()
    user.password_hash = hash_password(data.new_password)
    user.updated_by = user.id
    for pending in password_reset_token_repository.list_pending_for_user(db, user.id):
        pending.used_at = now
    user_repository.save(db, user)
    logger.info("Password set with token", extra={"user_id": user.id})
