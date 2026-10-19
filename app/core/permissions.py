from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.model_user import Role, User
from app.repositories import revoked_token_repository

ALL_ROLES = (Role.admin, Role.waiter, Role.kitchen, Role.bartender, Role.customer)
USERS = (Role.admin,)
MENU_READ = ALL_ROLES
MENU_WRITE = (Role.admin,)
TABLES = (Role.admin, Role.waiter)
RESERVATIONS = (Role.admin, Role.waiter, Role.customer)
ORDERS = (Role.admin, Role.waiter)
KITCHEN = (Role.admin, Role.kitchen)
BARTENDER = (Role.admin, Role.bartender)
INVOICES = (Role.admin, Role.waiter)
STATS = (Role.admin,)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise unauthorized

    # R-07: un jti revocado (logout) invalida el access token aunque no haya caducado
    if revoked_token_repository.is_revoked(db, payload["jti"]):
        raise unauthorized

    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role) -> Callable[[User], User]:
    allowed = {role.value for role in roles}

    def checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return user

    return checker


def ensure_owner_or_role(user: User, owner_id: int, *roles: Role) -> None:
    """403 si el usuario no es el dueño del recurso ni tiene uno de los roles (p. ej. reservas de customer)."""
    if user.id != owner_id and user.role not in {role.value for role in roles}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
