from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.permissions import CurrentUser
from app.core.security import create_access_token
from app.database import get_db
from app.schemas.schema_social import SocialLoginRequest, SocialProvider
from app.schemas.schema_user import UserOut, UserRegister
from app.services import social_auth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Auto-registro de cliente",
)
def register(data: UserRegister, db: DbSession):
    """Crea una cuenta `customer` activa al instante (R-03).

    No emite token: el usuario inicia sesión después con `POST /auth/login`.
    """
    return user_service.register_user(db, data)


@router.post("/login")
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    """Inicia sesión y devuelve un token JWT."""
    user = user_service.authenticate(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.post("/social/{provider}", summary="Login con Google o GitHub")
def social_login(provider: SocialProvider, data: SocialLoginRequest, db: DbSession):
    """Intercambia el `code` OAuth del proveedor y devuelve un token JWT (HU-38).

    Crea un `customer` si no existe, o vincula la cuenta si el email está verificado.
    """
    user = social_auth_service.login(db, provider, data)
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: CurrentUser):
    """Devuelve los datos del usuario autenticado."""
    return current_user
