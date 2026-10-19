from pydantic import BaseModel, ConfigDict, Field


class TokenOut(BaseModel):
    """Respuesta de `POST /auth/login`, `POST /auth/refresh` y `POST /auth/social/{provider}`."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "550e8400-e29b-41d4-a716-446655440000",
                    "token_type": "bearer",
                }
            ]
        }
    )

    access_token: str = Field(
        description="JWT para la cabecera `Authorization: Bearer <access_token>`."
    )
    refresh_token: str = Field(
        description="Token de renovación. Envíalo a `POST /auth/refresh` para obtener un par nuevo."
    )
    token_type: str = Field(default="bearer", description="Siempre `bearer`.")


class RefreshTokenIn(BaseModel):
    """Body para `POST /auth/refresh` y `POST /auth/logout`."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"refresh_token": "550e8400-e29b-41d4-a716-446655440000"}]
        }
    )

    refresh_token: str = Field(description="Refresh token recibido al iniciar sesión.")
