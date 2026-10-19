"""Tokens de un solo uso (R-09): se envía el token en claro y solo se guarda su hash."""

import hashlib
import secrets


def generate_token() -> str:
    """Genera un token aleatorio apto para URL."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Devuelve el SHA-256 del token en hexadecimal."""
    return hashlib.sha256(token.encode()).hexdigest()
