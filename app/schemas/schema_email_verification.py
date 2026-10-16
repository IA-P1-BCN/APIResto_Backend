"""Cuerpos de la verificación de email (HU-33, R-15) y respuesta común de los envíos."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

EMAIL_DISPATCH_DETAIL = "If the account exists, an email has been sent"


class EmailVerificationRequest(BaseModel):
    """Token del enlace del email de verificación (R-09)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"token": "token-del-enlace-del-email"}]},
    )

    token: str = Field(min_length=1, max_length=200, description="Token del enlace del email.")


class ResendVerificationRequest(BaseModel):
    """Email de la cuenta a la que reenviar el enlace de verificación (decisión J)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"email": "ana@example.com"}]},
    )

    email: EmailStr = Field(description="Se compara en minúsculas (R-01).")


class EmailDispatchOut(BaseModel):
    """Respuesta 202, igual exista o no la cuenta (decisión I)."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"detail": EMAIL_DISPATCH_DETAIL}]},
    )

    detail: str = Field(default=EMAIL_DISPATCH_DETAIL)
