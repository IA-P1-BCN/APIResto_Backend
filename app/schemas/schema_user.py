from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.model_user import Role

MIN_PASSWORD_LENGTH = 8


class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None

class UserCreate(UserBase):
    password: str
    role: Role = Role.customer

class UserRegister(UserBase):
    """Datos del auto-registro (R-03). El `role` del payload se ignora."""

    password: str = Field(
        min_length=MIN_PASSWORD_LENGTH,
        description=f"Contraseña, mínimo {MIN_PASSWORD_LENGTH} caracteres (R-02).",
    )
    role: Role | None = Field(
        default=None,
        description="Ignorado: el auto-registro siempre crea un `customer` (R-03).",
    )

class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    password: str | None = None
    role: Role | None = None

class UserProfileUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(
        min_length=MIN_PASSWORD_LENGTH,
        description=f"Contraseña nueva, mínimo {MIN_PASSWORD_LENGTH} caracteres (R-02).",
    )

class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    created_by: int | None = None
    updated_by: int | None = None
