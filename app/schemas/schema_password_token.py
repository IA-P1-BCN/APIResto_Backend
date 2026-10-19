from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.model_user import Role
from app.schemas.schema_user import MIN_PASSWORD_LENGTH


class UserInvite(BaseModel):
    """Alta de un usuario sin contraseña: la crea él con el enlace del email (HU-52)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "Lucía Gómez",
                    "email": "lucia@example.com",
                    "phone": "600123456",
                    "role": "customer",
                }
            ]
        },
    )

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(description="Se guarda en minúsculas; debe ser único (R-01).")
    phone: str | None = Field(default=None, max_length=20)
    role: Role = Field(default=Role.customer, description="Por defecto `customer`.")


class SetPasswordRequest(BaseModel):
    """Contraseña nueva con el token del enlace del email (HU-52, R-09)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"token": "token-del-enlace-del-email", "new_password": "MiClave2026"}]
        },
    )

    token: str = Field(min_length=1, max_length=200, description="Token del enlace del email.")
    new_password: str = Field(
        min_length=MIN_PASSWORD_LENGTH,
        description=f"Contraseña nueva, mínimo {MIN_PASSWORD_LENGTH} caracteres (R-02).",
    )


class ForgotPasswordRequest(BaseModel):
    """Email de la cuenta que ha olvidado su contraseña (HU-33, decisiones F e I)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"email": "ana@example.com"}]},
    )

    email: EmailStr = Field(description="Se compara en minúsculas (R-01).")
