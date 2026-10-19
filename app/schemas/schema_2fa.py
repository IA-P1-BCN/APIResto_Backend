from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CODE_DESCRIPTION = "Código de 6 dígitos de la app de autenticación o un código de recuperación."


class TwoFactorChallengeOut(BaseModel):
    """Respuesta del login cuando la cuenta tiene la verificación en dos pasos (HU-37)."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"mfa_required": True, "mfa_token": "eyJhbGciOiJIUzI1NiIs..."}]}
    )

    mfa_required: Literal[True] = Field(
        default=True, description="Falta el código: se envía con `POST /auth/2fa/verify`."
    )
    mfa_token: str = Field(description="Token temporal (5 min) que solo sirve para `POST /auth/2fa/verify`.")


class TwoFactorVerifyRequest(BaseModel):
    """Segundo paso del login: el token temporal y el código."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"mfa_token": "eyJhbGciOiJIUzI1NiIs...", "code": "123456"}]},
    )

    mfa_token: str = Field(min_length=1, max_length=2000)
    code: str = Field(min_length=6, max_length=32, description=CODE_DESCRIPTION)


class TwoFactorCodeRequest(BaseModel):
    """Código para activar o desactivar la verificación en dos pasos."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{"code": "123456"}]})

    code: str = Field(min_length=6, max_length=32, description=CODE_DESCRIPTION)


class TwoFactorStatusOut(BaseModel):
    """Estado de la verificación en dos pasos del usuario autenticado."""

    enabled: bool
    recovery_codes_left: int = Field(description="Códigos de recuperación sin usar.")


class TwoFactorSetupOut(BaseModel):
    """Secreto nuevo, aún sin activar, para añadirlo a la app de autenticación."""

    secret: str = Field(description="Secreto en base32, para teclearlo a mano si no se puede escanear el QR.")
    otpauth_uri: str = Field(description="URI `otpauth://` que contiene el QR.")
    qr_svg: str = Field(description="QR en SVG con la URI `otpauth://`.")


class RecoveryCodesOut(BaseModel):
    """Códigos de recuperación de un solo uso. Solo se muestran al activar."""

    recovery_codes: list[str]
