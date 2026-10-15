"""Cliente HTTP de Google y GitHub: intercambia el `code` y devuelve el perfil (HU-38).

Aislado del resto para poder mockear `httpx` en los tests. Nunca registra el `code`,
los tokens del proveedor ni los secretos.
"""

import logging

import httpx

from app.config import settings
from app.core.exceptions import (
    BadGatewayError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from app.schemas.schema_social import SocialProfile, SocialProvider

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def _credentials(provider: SocialProvider) -> tuple[str, str]:
    client_id = getattr(settings, f"{provider.value.upper()}_CLIENT_ID")
    client_secret = getattr(settings, f"{provider.value.upper()}_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ServiceUnavailableError(
            f"Login with {provider.value} is not configured", code="provider_not_configured"
        )
    return client_id, client_secret


def _unavailable(provider: SocialProvider, reason: str) -> BadGatewayError:
    logger.warning("Social provider failed provider=%s reason=%s", provider.value, reason)
    return BadGatewayError(f"{provider.value} is not available", code="provider_unavailable")


def _invalid_code() -> UnauthorizedError:
    return UnauthorizedError("Invalid or expired authorization code", code="invalid_code")


def _request(provider: SocialProvider, method: str, url: str, **kwargs) -> httpx.Response:
    try:
        return httpx.request(method, url, timeout=TIMEOUT_SECONDS, **kwargs)
    except httpx.HTTPError as exc:
        raise _unavailable(provider, type(exc).__name__) from exc


def _json(provider: SocialProvider, response: httpx.Response):
    try:
        return response.json()
    except ValueError as exc:
        raise _unavailable(provider, "invalid_json") from exc


def _google_profile(code: str, redirect_uri: str) -> SocialProfile:
    provider = SocialProvider.google
    client_id, client_secret = _credentials(provider)
    token_response = _request(
        provider,
        "POST",
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    if 400 <= token_response.status_code < 500:
        raise _invalid_code()
    if token_response.status_code != 200:
        raise _unavailable(provider, f"token_status_{token_response.status_code}")
    access_token = _json(provider, token_response).get("access_token")
    if not access_token:
        raise _invalid_code()

    info_response = _request(
        provider, "GET", GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
    )
    if info_response.status_code != 200:
        raise _unavailable(provider, f"userinfo_status_{info_response.status_code}")
    info = _json(provider, info_response)
    if not info.get("sub"):
        raise _unavailable(provider, "missing_sub")
    return SocialProfile(
        provider_user_id=str(info["sub"]),
        email=info.get("email"),
        email_verified=info.get("email_verified") is True,
        name=info.get("name"),
    )


def _github_profile(code: str, redirect_uri: str) -> SocialProfile:
    provider = SocialProvider.github
    client_id, client_secret = _credentials(provider)
    token_response = _request(
        provider,
        "POST",
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )
    if token_response.status_code != 200:
        raise _unavailable(provider, f"token_status_{token_response.status_code}")
    access_token = _json(provider, token_response).get("access_token")
    if not access_token:
        raise _invalid_code()

    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"}
    user_response = _request(provider, "GET", GITHUB_USER_URL, headers=headers)
    emails_response = _request(provider, "GET", GITHUB_EMAILS_URL, headers=headers)
    for response in (user_response, emails_response):
        if response.status_code != 200:
            raise _unavailable(provider, f"api_status_{response.status_code}")
    user = _json(provider, user_response)
    emails = _json(provider, emails_response)
    if not user.get("id"):
        raise _unavailable(provider, "missing_id")

    primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
    return SocialProfile(
        provider_user_id=str(user["id"]),
        email=primary["email"] if primary else None,
        email_verified=primary is not None,
        name=user.get("name") or user.get("login"),
    )


def fetch_profile(provider: SocialProvider, code: str, redirect_uri: str) -> SocialProfile:
    """Intercambia el `code` por el perfil del usuario en el proveedor."""
    if provider is SocialProvider.google:
        return _google_profile(code, redirect_uri)
    return _github_profile(code, redirect_uri)
