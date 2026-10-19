from datetime import datetime

from sqlalchemy import Column, DateTime, String

from app.database import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti = Column(String(36), primary_key=True)
    expires_at = Column(DateTime, nullable=False)  # cuándo caduca el access token (para purgar)
    revoked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
