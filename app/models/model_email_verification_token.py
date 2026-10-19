from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


class EmailVerificationToken(Base):
    """Token de un solo uso para verificar el email (HU-33, R-09, R-15). Solo se guarda su hash."""

    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
