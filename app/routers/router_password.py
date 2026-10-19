"""Invitar a un usuario y que cree su propia contraseña con el enlace del email (HU-52).

También la recuperación de contraseña: `forgot-password` envía el enlace y la contraseña
se fija con el mismo `set-password` (HU-33, decisión F).
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.openapi import error_responses
from app.core.permissions import USERS, CurrentUser, require_role
from app.database import get_db
from app.models.model_user import User
from app.schemas.schema_email_verification import EmailDispatchOut
from app.schemas.schema_password_token import (
    ForgotPasswordRequest,
    SetPasswordRequest,
    UserInvite,
)
from app.schemas.schema_user import UserOut
from app.services import password_token_service
from app.services.auth_emails import password_reset_email
from app.services.notifications import send_email

invite_router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_role(*USERS))],
)

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


@invite_router.post(
    "/invite",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Invitar a un usuario para que cree su contraseña",
    responses=error_responses(
        401,
        403,
        409,
        422,
        descriptions={
            401: "Falta el token o no es válido.",
            403: "Solo admin.",
            409: "El email ya está registrado (`conflict`).",
            422: "Datos no válidos (`validation_error`).",
        },
    ),
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
    Rol: admin.
    """
    user, token = password_token_service.invite_user(db, data, actor)
    background_tasks.add_task(send_email, *password_token_service.invitation_email(user, token))
    return user


@router.post(
    "/set-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Crear la contraseña con el enlace del email",
    responses=error_responses(
        400,
        410,
        422,
        descriptions={
            400: "Token desconocido, o usuario desactivado o borrado (`invalid_token`).",
            410: "Token ya usado (`token_used`) o caducado (`token_expired`).",
            422: "Datos no válidos o contraseña de menos de 8 caracteres "
            "(`validation_error`).",
        },
    ),
)
def set_password(data: SetPasswordRequest, db: DbSession) -> Response:
    """Fija la contraseña del usuario del token (R-02, R-09). Sin cuerpo.

    Después el usuario inicia sesión con `POST /auth/login`. Rol: público.
    """
    password_token_service.set_password(db, data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/forgot-password",
    response_model=EmailDispatchOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pedir un enlace para restablecer la contraseña",
    responses=error_responses(
        422,
        descriptions={422: "Email mal formado o campos de más (`validation_error`)."},
    ),
)
def forgot_password(
    data: ForgotPasswordRequest,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> EmailDispatchOut:
    """Envía un enlace para fijar una contraseña nueva con `POST /auth/set-password` (HU-33).

    Responde siempre 202 con el mismo cuerpo, exista o no la cuenta (decisión I). El enlace
    es de un solo uso y caduca a las `PASSWORD_RESET_EXPIRE_HOURS` (R-09, decisión G).
    Sirve también a cuentas sin contraseña (decisión N). No se envía otro enlace hasta
    pasados `TOKEN_RESEND_COOLDOWN_SECONDS`, sin 429 (decisión M). Rol: público.
    """
    result = password_token_service.forgot_password(db, data.email)
    if result is not None:
        background_tasks.add_task(send_email, *password_reset_email(*result))
    return EmailDispatchOut()
