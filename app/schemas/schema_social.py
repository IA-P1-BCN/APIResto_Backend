from enum import Enum

from pydantic import BaseModel, Field


class SocialProvider(str, Enum):
    google = "google"
    github = "github"


class SocialLoginRequest(BaseModel):
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
