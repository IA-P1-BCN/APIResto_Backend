from datetime import UTC, datetime

import httpx
import pytest

from app.config import settings
from app.models.model_social_account import SocialAccount
from app.models.model_user import User
from app.services import social_providers as providers

REDIRECT = "http://localhost:5173/auth/callback"
BODY = {"code": "abc123", "redirect_uri": REDIRECT}

GOOGLE_PROFILE = {"sub": "g-1", "email": "Ana@Gmail.com", "email_verified": True, "name": "Ana Gómez"}
GITHUB_USER = {"id": 42, "login": "anagh", "name": "Ana GH"}
GITHUB_EMAILS = [
    {"email": "other@x.com", "primary": False, "verified": True},
    {"email": "ana@gh.com", "primary": True, "verified": True},
]


def _response(status: int, payload) -> httpx.Response:
    return httpx.Response(status, json=payload, request=httpx.Request("GET", "http://test"))


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    for name in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"):
        monkeypatch.setattr(settings, name, "test-value")


@pytest.fixture
def provider_api(monkeypatch):
    """Sustituye httpx.request: responses[url] = (status, json) o una excepción."""
    responses = {
        providers.GOOGLE_TOKEN_URL: (200, {"access_token": "tok"}),
        providers.GOOGLE_USERINFO_URL: (200, GOOGLE_PROFILE),
        providers.GITHUB_TOKEN_URL: (200, {"access_token": "tok"}),
        providers.GITHUB_USER_URL: (200, GITHUB_USER),
        providers.GITHUB_EMAILS_URL: (200, GITHUB_EMAILS),
    }
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        outcome = responses[url]
        if isinstance(outcome, Exception):
            raise outcome
        return _response(*outcome)

    monkeypatch.setattr(providers.httpx, "request", fake_request)
    responses["calls"] = calls
    return responses


def _login(client, provider="google", body=BODY):
    return client.post(f"/auth/social/{provider}", json=body)


def _me(client, token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()


def test_google_creates_customer_without_password(client, db, provider_api):
    r = _login(client)
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    me = _me(client, r.json()["access_token"])
    assert me["email"] == "ana@gmail.com"
    assert me["role"] == "customer"
    assert me["name"] == "Ana Gómez"
    user = db.query(User).filter(User.email == "ana@gmail.com").one()
    assert user.password_hash is None
    account = db.query(SocialAccount).one()
    assert (account.user_id, account.provider, account.provider_user_id) == (user.id, "google", "g-1")


def test_github_uses_primary_verified_email(client, db, provider_api):
    r = _login(client, "github")
    assert r.status_code == 200
    assert _me(client, r.json()["access_token"])["email"] == "ana@gh.com"
    assert db.query(SocialAccount).one().provider == "github"


def test_github_name_falls_back_to_login(client, provider_api):
    provider_api[providers.GITHUB_USER_URL] = (200, {"id": 7, "login": "solo-login", "name": None})
    r = _login(client, "github")
    assert _me(client, r.json()["access_token"])["name"] == "solo-login"


def test_second_login_reuses_account(client, db, provider_api):
    first = _login(client).json()["access_token"]
    second = _login(client).json()["access_token"]
    assert _me(client, first)["id"] == _me(client, second)["id"]
    assert db.query(SocialAccount).count() == 1
    assert db.query(User).filter(User.email == "ana@gmail.com").count() == 1


def test_links_existing_user_with_verified_email(client, db, make_user, provider_api):
    staff = make_user("waiter", email="ana@gmail.com")
    r = _login(client)
    assert r.status_code == 200
    me = _me(client, r.json()["access_token"])
    assert (me["id"], me["role"]) == (staff.id, "waiter")
    assert db.query(SocialAccount).one().user_id == staff.id


def test_unverified_email_is_401_and_not_linked(client, db, make_user, provider_api):
    make_user("customer", email="ana@gmail.com")
    provider_api[providers.GOOGLE_USERINFO_URL] = (200, {**GOOGLE_PROFILE, "email_verified": False})
    r = _login(client)
    assert r.status_code == 401
    assert r.json()["code"] == "email_not_verified"
    assert db.query(SocialAccount).count() == 0


def test_github_without_verified_primary_email_is_401(client, provider_api):
    provider_api[providers.GITHUB_EMAILS_URL] = (200, [{"email": "a@b.com", "primary": True, "verified": False}])
    assert _login(client, "github").status_code == 401


def test_inactive_user_is_401(client, make_user, provider_api):
    make_user("customer", email="ana@gmail.com", is_active=False)
    r = _login(client)
    assert r.status_code == 401
    assert r.json()["code"] == "inactive_account"


def test_deleted_user_is_401_even_with_linked_account(client, db, provider_api):
    token = _login(client).json()["access_token"]
    user = db.get(User, _me(client, token)["id"])
    user.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    user.is_active = False
    db.commit()
    assert _login(client).status_code == 401


def test_invalid_code_is_401(client, provider_api):
    provider_api[providers.GOOGLE_TOKEN_URL] = (400, {"error": "invalid_grant"})
    r = _login(client)
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_code"


def test_github_error_without_token_is_401(client, provider_api):
    provider_api[providers.GITHUB_TOKEN_URL] = (200, {"error": "bad_verification_code"})
    assert _login(client, "github").status_code == 401


def test_provider_down_is_502(client, provider_api):
    provider_api[providers.GOOGLE_TOKEN_URL] = httpx.ConnectError("sin red")
    r = _login(client)
    assert r.status_code == 502
    assert r.json()["code"] == "provider_unavailable"


def test_provider_server_error_is_502(client, provider_api):
    provider_api[providers.GITHUB_USER_URL] = (500, {})
    assert _login(client, "github").status_code == 502


def test_provider_not_configured_is_503(client, monkeypatch, provider_api):
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", "")
    r = _login(client, "github")
    assert r.status_code == 503
    assert r.json()["code"] == "provider_not_configured"


def test_unknown_provider_is_422(client, provider_api):
    assert _login(client, "facebook").status_code == 422


def test_redirect_uri_must_be_allowed(client, provider_api):
    r = _login(client, body={"code": "x", "redirect_uri": "https://evil.example/cb"})
    assert r.status_code == 422
    assert r.json()["code"] == "redirect_uri_not_allowed"
    assert not [c for c in provider_api["calls"]]


def test_missing_code_is_422(client, provider_api):
    assert _login(client, body={"redirect_uri": REDIRECT}).status_code == 422


def test_user_without_password_cannot_use_password_login(client, provider_api):
    _login(client)
    r = client.post("/auth/login", data={"username": "ana@gmail.com", "password": "cualquiera123"})
    assert r.status_code == 401


def test_secrets_and_code_are_not_logged(client, provider_api, caplog):
    provider_api[providers.GOOGLE_TOKEN_URL] = (500, {})
    with caplog.at_level("DEBUG"):
        _login(client)
    assert "abc123" not in caplog.text
    assert "test-value" not in caplog.text


@pytest.mark.parametrize(
    ("provider", "url", "outcome"),
    [
        ("google", providers.GOOGLE_USERINFO_URL, (500, {})),
        ("google", providers.GOOGLE_USERINFO_URL, (200, {k: v for k, v in GOOGLE_PROFILE.items() if k != "sub"})),
        ("github", providers.GITHUB_TOKEN_URL, (500, {})),
        ("github", providers.GITHUB_USER_URL, (200, {k: v for k, v in GITHUB_USER.items() if k != "id"})),
    ],
)
def test_provider_bad_responses_are_502(client, provider_api, provider, url, outcome):
    provider_api[url] = outcome
    r = _login(client, provider)
    assert r.status_code == 502
    assert r.json()["code"] == "provider_unavailable"


def test_google_token_without_access_token_is_401(client, provider_api):
    provider_api[providers.GOOGLE_TOKEN_URL] = (200, {})
    r = _login(client)
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_code"


def test_provider_invalid_json_is_502(client, monkeypatch):
    monkeypatch.setattr(
        providers.httpx,
        "request",
        lambda *a, **k: httpx.Response(200, content=b"<html>", request=httpx.Request("POST", "http://test")),
    )
    r = _login(client)
    assert r.status_code == 502
    assert r.json()["code"] == "provider_unavailable"
