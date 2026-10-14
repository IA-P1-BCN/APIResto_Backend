from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.permissions import CurrentUser
from app.core.security import create_access_token
from app.database import get_db
from app.schemas.schema_user import UserOut, UserRegister
from app.services import user_service

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


@router.get("/me", response_model=UserOut)
def get_me(current_user: CurrentUser):
    """Devuelve los datos del usuario autenticado."""
    return current_user
