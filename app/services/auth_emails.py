"""Emails de verificación de email y de recuperación de contraseña (HU-33, R-15).

Funciones puras: arman (to, subject, html) a partir del usuario y del token en claro.
No envían nada ni registran el token o el enlace; el envío lo hacen los routers con
`send_email` en `BackgroundTasks`.
"""

from html import escape

from app.config import settings
from app.models.model_user import User

VERIFY_EMAIL_PATH = "/verificar-email"
PASSWORD_RESET_PATH = "/restablecer-contrasena"
VERIFICATION_SUBJECT = "Verifica tu email de APIResto"
PASSWORD_RESET_SUBJECT = "Restablece tu contraseña de APIResto"


def _link(path: str, token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}?token={token}"


def _hours_text(hours: int) -> str:
    """'1 hora' o 'N horas'."""
    return f"{hours} hora" if hours == 1 else f"{hours} horas"


def verification_link(token: str) -> str:
    return _link(VERIFY_EMAIL_PATH, token)


def password_reset_link(token: str) -> str:
    return _link(PASSWORD_RESET_PATH, token)


def verification_email(user: User, token: str) -> tuple[str, str, str]:
    """(to, subject, html) del email con el enlace para verificar el email."""
    link = escape(verification_link(token), quote=True)
    hours = _hours_text(settings.EMAIL_VERIFY_EXPIRE_HOURS)
    html = (
        f"<p>Hola {escape(user.name)}:</p>"
        "<p>Para confirmar que este email es tuyo, pulsa el enlace:</p>"
        f'<p><a href="{link}">Verificar mi email</a></p>'
        f"<p>El enlace caduca en {hours} y solo se puede usar una vez. "
        "Si caduca, puedes pedir otro desde la aplicación.</p>"
        "<p>APIResto</p>"
    )
    return user.email, VERIFICATION_SUBJECT, html


def password_reset_email(user: User, token: str) -> tuple[str, str, str]:
    """(to, subject, html) del email con el enlace para restablecer la contraseña."""
    link = escape(password_reset_link(token), quote=True)
    hours = _hours_text(settings.PASSWORD_RESET_EXPIRE_HOURS)
    html = (
        f"<p>Hola {escape(user.name)}:</p>"
        "<p>Hemos recibido una petición para restablecer la contraseña de tu cuenta "
        "de APIResto. Para elegir una nueva, pulsa el enlace:</p>"
        f'<p><a href="{link}">Restablecer mi contraseña</a></p>'
        f"<p>El enlace caduca en {hours} y solo se puede usar una vez.</p>"
        "<p>Si no lo has pedido tú, ignora este email: tu contraseña no cambiará.</p>"
        "<p>APIResto</p>"
    )
    return user.email, PASSWORD_RESET_SUBJECT, html
