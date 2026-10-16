"""Invitar a un usuario y que cree su propia contraseña con el enlace del email (HU-52)."""

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.exceptions import ErrorResponse
from app.core.permissions import USERS, CurrentUser, require_role
from app.database import get_db
from app.models.model_user import User
from app.schemas.schema_password_token import SetPasswordRequest, UserInvite
from app.schemas.schema_user import UserOut
from app.services import password_token_service
from app.services.notifications import send_email

invite_router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_role(*USERS))],
)

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


def _errors(descriptions: dict[int, str]) -> dict[int | str, dict[str, Any]]:
    return {
        code: {"model": ErrorResponse, "description": description}
        for code, description in descriptions.items()
    }


@invite_router.post(
    "/invite",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Invitar a un usuario para que cree su contraseña",
    responses=_errors({
        401: "Falta el token o no es válido.",
        403: "Solo admin.",
        409: "El email ya está registrado (`conflict`).",
        422: "Datos no válidos (`validation_error`).",
    }),
)
def invite_user(
    data: UserInvite,
    db: DbSession,
    actor: CurrentUser,
    background_tasks: BackgroundTasks,
) -> User:
    """Crea el usuario sin contraseña y le envía un email con un enlace para crearla.

    El enlace lleva un token de un solo uso que caduca (`PASSWORD_TOKEN_EXPIRE_HOURS`).
    El email se envía en segundo plano; con `EMAIL_ENABLED=false` solo se registra.
    """
    user, token = password_token_service.invite_user(db, data, actor)
    background_tasks.add_task(send_email, *password_token_service.invitation_email(user, token))
    return user


@router.post(
    "/set-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Crear la contraseña con el enlace del email",
    responses=_errors({
        400: "Token desconocido, o usuario desactivado o borrado (`invalid_token`).",
        410: "Token ya usado (`token_used`) o caducado (`token_expired`).",
        422: "Datos no válidos o contraseña de menos de 8 caracteres (`validation_error`).",
    }),
)
def set_password(data: SetPasswordRequest, db: DbSession) -> Response:
    """Público. Fija la contraseña del usuario del token (R-02, R-09). Sin cuerpo.

    Después el usuario inicia sesión con `POST /auth/login`.
    """
    password_token_service.set_password(db, data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
