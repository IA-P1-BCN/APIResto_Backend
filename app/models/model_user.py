import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    false,
    func,
)

from app.database import Base


class Role(str, enum.Enum):
    admin = "admin"
    waiter = "waiter"
    kitchen = "kitchen"
    bartender = "bartender"
    customer = "customer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    phone = Column(String(20))
    role = Column(String(20), nullable=False, default=Role.customer.value, server_default=Role.customer.value)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, nullable=False, default=False, server_default=false())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    totp_secret = Column(String(255), nullable=True)
    totp_enabled = Column(Boolean, nullable=False, default=False, server_default=false())
    totp_recovery_codes = Column(String(600), nullable=True)
