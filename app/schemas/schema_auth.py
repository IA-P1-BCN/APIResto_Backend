from pydantic import BaseModel, ConfigDict, Field


class TokenOut(BaseModel):
    """Respuesta de `POST /auth/login` y `POST /auth/social/{provider}`."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer"}
            ]
        }
    )

    access_token: str = Field(
        description="JWT para la cabecera `Authorization: Bearer <access_token>`."
    )
    token_type: str = Field(default="bearer", description="Siempre `bearer`.")
