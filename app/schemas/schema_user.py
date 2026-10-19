from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.model_user import Role

MIN_PASSWORD_LENGTH = 8


class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None

class UserCreate(UserBase):
    """Alta de un usuario por un admin, con cualquier rol (R-03)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "José Ruiz",
                    "email": "jose@example.com",
                    "phone": "600654321",
                    "password": "secreto123",
                    "role": "waiter",
                }
            ]
        }
    )

    password: str
    role: Role = Role.customer

class UserRegister(UserBase):
    """Datos del auto-registro (R-03). El `role` del payload se ignora."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Ana Gómez",
                    "email": "ana@example.com",
                    "phone": "600123456",
                    "password": "secreto123",
                }
            ]
        }
    )

    password: str = Field(
        min_length=MIN_PASSWORD_LENGTH,
        description=f"Contraseña, mínimo {MIN_PASSWORD_LENGTH} caracteres (R-02).",
    )
    role: Role | None = Field(
        default=None,
        description="Ignorado: el auto-registro siempre crea un `customer` (R-03).",
    )

class UserUpdate(BaseModel):
    """Edición por un admin. Solo se aplican los campos enviados."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"role": "kitchen"},
                {"name": "José Ruiz Martín", "phone": "600111222"},
            ]
        }
    )

    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    password: str | None = None
    role: Role | None = None

class UserProfileUpdate(BaseModel):
    """Edición del propio perfil. Solo se aplican los campos enviados; `name` y `email` no admiten `null`."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"name": "Ana López", "email": "ana@example.com", "phone": "600123456"},
                {"phone": None},
            ]
        },
    )

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = Field(
        default=None,
        description="Se guarda en minúsculas; debe ser único (R-01).",
    )
    phone: str | None = Field(
        default=None,
        max_length=20,
        description="`null` borra el teléfono.",
    )

    @field_validator("name", "email")
    @classmethod
    def reject_null(cls, value):
        """Rechaza `null` explícito en campos que no se pueden borrar."""
        if value is None:
            raise ValueError("Field cannot be null")
        return value

class PasswordChange(BaseModel):
    """Cambio de la propia contraseña indicando la actual."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"current_password": "OldPassw0rd", "new_password": "NewPassw0rd"},
            ]
        },
    )

    current_password: str = Field(min_length=1, description="Contraseña actual.")
    new_password: str = Field(
        min_length=MIN_PASSWORD_LENGTH,
        description=f"Nueva contraseña, mínimo {MIN_PASSWORD_LENGTH} caracteres (R-02).",
    )

class UserOut(UserBase):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 7,
                    "name": "Ana Gómez",
                    "email": "ana@example.com",
                    "phone": "600123456",
                    "role": "customer",
                    "is_active": True,
                    "email_verified": False,
                    "created_at": "2026-10-14T10:15:00",
                    "updated_at": None,
                    "deleted_at": None,
                    "created_by": None,
                    "updated_by": None,
                }
            ]
        },
    )

    id: int
    role: Role
    is_active: bool
    email_verified: bool = Field(
        description="Si el email está verificado (R-15). Informativo: no impide iniciar sesión."
    )
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    created_by: int | None = None
    updated_by: int | None = None
