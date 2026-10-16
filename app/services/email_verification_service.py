"""Verificación de email (HU-33, R-15): informativa, el login no la comprueba (decisión A).

Los tokens son de un solo uso y caducan a las EMAIL_VERIFY_EXPIRE_HOURS horas (R-09).
Solo se guarda su SHA-256; el valor en claro va únicamente en el email y nunca se
registra en el log. Este servicio no envía emails: devuelve el token y el router encola
el envío.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import AppError
from app.core.one_time_tokens import generate_token, hash_token
from app.models.model_email_verification_token import EmailVerificationToken
from app.models.model_user import User
from app.repositories import email_verification_token_repository, user_repository
from app.schemas.schema_user import UserProfileUpdate, UserRegister
from app.services import user_service
from app.services.password_token_service import TokenGoneError

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def issue_verification_token(db: Session, user: User) -> str:
    """Crea un `EmailVerificationToken` para el usuario y devuelve el valor en claro."""
    token = generate_token()
    now = _now()
    email_verification_token_repository.add(
        db,
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(hours=settings.EMAIL_VERIFY_EXPIRE_HOURS),
        ),
    )
    logger.info("Email verification token issued", extra={"user_id": user.id})
    return token


def _invalid_token(user_id: int | None = None) -> AppError:
    logger.warning("Email verification rejected", extra={"user_id": user_id, "code": "invalid_token"})
    return AppError("Invalid token", code="invalid_token")


def _gone(detail: str, code: str, user_id: int) -> TokenGoneError:
    logger.warning("Email verification rejected", extra={"user_id": user_id, "code": code})
    return TokenGoneError(detail, code=code)


def verify_email(db: Session, token: str) -> None:
    """Verifica el email con el token y marca como usados todos los pendientes (R-09, decisión L).

    Desconocido, o usuario inactivo o borrado (R-04) → 400 `invalid_token`; usado → 410
    `token_used`; caducado → 410 `token_expired`. Si la cuenta ya estaba verificada, el token
    se consume igualmente sin error.
    """
    record = email_verification_token_repository.get_by_hash_for_update(db, hash_token(token))
    if record is None:
        raise _invalid_token()
    if record.used_at is not None:
        raise _gone("Token already used", "token_used", record.user_id)
    if record.expires_at <= _now():
        raise _gone("Token expired", "token_expired", record.user_id)

    user = user_repository.get_by_id(db, record.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise _invalid_token(record.user_id)

    now = _now()
    user.email_verified = True
    user.updated_by = user.id
    record.used_at = now
    for pending in email_verification_token_repository.list_pending_for_user(db, user.id):
        pending.used_at = now
    user_repository.save(db, user)
    logger.info("Email verified", extra={"user_id": user.id})


def _in_cooldown(db: Session, user: User) -> bool:
    """Decisión M: el último token del usuario se creó hace menos del tiempo de espera."""
    latest = email_verification_token_repository.get_latest_for_user(db, user.id)
    if latest is None or latest.created_at is None:
        return False
    return latest.created_at > _now() - timedelta(seconds=settings.TOKEN_RESEND_COOLDOWN_SECONDS)


def resend_verification(db: Session, email: str) -> tuple[User, str] | None:
    """Emite otro token de verificación (decisiones I, J, M).

    Devuelve `(user, token)` para enviar el email, o `None` si la cuenta no existe, está
    inactiva o borrada (R-04), ya está verificada o está en el tiempo de espera. El router
    responde 202 igual en todos los casos.
    """
    user = user_repository.get_by_email(db, user_service.normalize_email(email))
    if user is None or not user.is_active or user.deleted_at is not None:
        logger.info("Verification email not sent", extra={"reason": "no_eligible_account"})
        return None
    if user.email_verified:
        logger.info("Verification email not sent", extra={"reason": "already_verified"})
        return None
    if _in_cooldown(db, user):
        logger.info("Verification email not sent", extra={"reason": "cooldown"})
        return None
    return user, issue_verification_token(db, user)


def register_user(db: Session, data: UserRegister) -> tuple[User, str]:
    """Auto-registro (decisión D): nace sin verificar y recibe su token, sin tiempo de espera."""
    user = user_service.register_user(db, data)
    return user, issue_verification_token(db, user)


def update_profile(db: Session, user: User, data: UserProfileUpdate) -> tuple[User, str | None]:
    """Edita el propio perfil; si el email cambia, vuelve a pedir la verificación (decisión E).

    Pone `email_verified = false`, invalida los tokens pendientes (iban a la dirección
    anterior) y devuelve un token nuevo, sin tiempo de espera. Si no cambia → `(user, None)`.
    """
    previous_email = user.email
    user = user_service.update_profile(db, user, data)
    if user.email == previous_email:
        return user, None

    now = _now()
    user.email_verified = False
    for pending in email_verification_token_repository.list_pending_for_user(db, user.id):
        pending.used_at = now
    user = user_repository.save(db, user)
    logger.info("Email changed, verification required", extra={"user_id": user.id})
    return user, issue_verification_token(db, user)
