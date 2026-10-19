from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SocialProvider(str, Enum):
    google = "google"
    github = "github"


class SocialLoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "code": "4/0AfJohXn-example-code",
                    "redirect_uri": "https://app.example.com/auth/callback",
                }
            ]
        }
    )

    code: str = Field(min_length=1, description="`code` que el proveedor devolvió al frontend.")
    redirect_uri: str = Field(
        min_length=1,
        description="Misma `redirect_uri` usada al redirigir al proveedor; debe pertenecer a un origen permitido.",
    )


class SocialProfile(BaseModel):
    """Datos del usuario en el proveedor que necesita el login."""

    provider_user_id: str
    email: str | None = None
    email_verified: bool = False
    name: str | None = None
