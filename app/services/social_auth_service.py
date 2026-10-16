import logging
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import UnauthorizedError, UnprocessableError
from app.models.model_social_account import SocialAccount
from app.models.model_user import Role, User
from app.repositories import social_account_repository, user_repository
from app.schemas.schema_social import SocialLoginRequest, SocialProfile, SocialProvider
from app.services import social_providers
from app.services.user_service import normalize_email

logger = logging.getLogger(__name__)

NAME_MAX_LENGTH = 100


def _origin(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    return parsed.scheme, parsed.netloc


def _ensure_allowed_redirect(redirect_uri: str) -> None:
    allowed = {
        _origin(origin.strip()) for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()
    }
    if _origin(redirect_uri) not in allowed:
        raise UnprocessableError("redirect_uri is not allowed", code="redirect_uri_not_allowed")


def _ensure_can_log_in(user: User) -> User:
    if not user.is_active or user.deleted_at is not None:
        raise UnauthorizedError("Account is not active", code="inactive_account")
    return user


def _display_name(profile: SocialProfile, email: str) -> str:
    return (profile.name or email.split("@")[0])[:NAME_MAX_LENGTH]


def _link(db: Session, user: User, provider: SocialProvider, profile: SocialProfile) -> None:
    social_account_repository.add(
        db,
        SocialAccount(
            user_id=user.id, provider=provider.value, provider_user_id=profile.provider_user_id
        ),
    )


def login(db: Session, provider: SocialProvider, data: SocialLoginRequest) -> User:
    """Inicia sesión con Google o GitHub: entra, vincula o crea el usuario (R-13).

    Al crear o vincular, el email queda verificado: lo verificó el proveedor (R-15, C, P1).
    """
    _ensure_allowed_redirect(data.redirect_uri)
    profile = social_providers.fetch_profile(provider, data.code, data.redirect_uri)

    account = social_account_repository.get(db, provider.value, profile.provider_user_id)
    if account:
        return _ensure_can_log_in(user_repository.get_by_id(db, account.user_id))

    if not profile.email or not profile.email_verified:
        raise UnauthorizedError("The provider has no verified email", code="email_not_verified")

    email = normalize_email(profile.email)
    user = user_repository.get_by_email(db, email)
    if user:
        _ensure_can_log_in(user)
        user.email_verified = True
    else:
        user = user_repository.add(
            db,
            User(
                name=_display_name(profile, email),
                email=email,
                password_hash=None,
                role=Role.customer.value,
                email_verified=True,
            ),
        )
    _link(db, user, provider, profile)
    logger.info("Social login linked provider=%s user_id=%s", provider.value, user.id)
    return user
