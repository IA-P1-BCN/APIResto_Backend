"""Verificación de email (HU-33, R-15): informativa, el login no la comprueba (decisión A)."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.openapi import error_responses
from app.database import get_db
from app.schemas.schema_email_verification import (
    EmailDispatchOut,
    EmailVerificationRequest,
    ResendVerificationRequest,
)
from app.services import email_verification_service
from app.services.auth_emails import verification_email
from app.services.notifications import send_email

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/verify-email",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Verificar el email con el enlace del email",
    responses=error_responses(
        400,
        410,
        422,
        descriptions={
            400: "Token desconocido, o usuario desactivado o borrado (`invalid_token`).",
            410: "Token ya usado (`token_used`) o caducado (`token_expired`).",
            422: "Falta el `token` o hay campos de más (`validation_error`).",
        },
    ),
)
def verify_email(data: EmailVerificationRequest, db: DbSession) -> Response:
    """Marca el email del usuario del token como verificado (R-09, R-15). Sin cuerpo.

    El token es de un solo uso y caduca (`EMAIL_VERIFY_EXPIRE_HOURS`); al usarlo se
    invalidan también los demás enlaces pendientes del usuario. Si la cuenta ya estaba
    verificada responde igualmente 204 (decisión L). Rol: público.
    """
    email_verification_service.verify_email(db, data.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/resend-verification",
    response_model=EmailDispatchOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reenviar el email de verificación",
    responses=error_responses(
        422,
        descriptions={422: "Email mal formado o campos de más (`validation_error`)."},
    ),
)
def resend_verification(
    data: ResendVerificationRequest,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> EmailDispatchOut:
    """Envía otro enlace de verificación si la cuenta existe, está activa y no está verificada.

    Responde siempre 202 con el mismo cuerpo, exista o no la cuenta (decisiones I y J).
    No se envía otro enlace hasta pasados `TOKEN_RESEND_COOLDOWN_SECONDS` desde el último,
    sin 429 (decisión M). El email se envía en segundo plano. Rol: público.
    """
    result = email_verification_service.resend_verification(db, data.email)
    if result is not None:
        background_tasks.add_task(send_email, *verification_email(*result))
    return EmailDispatchOut()
