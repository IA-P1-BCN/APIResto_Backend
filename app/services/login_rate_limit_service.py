"""Límite de intentos de login por IP y email (HU-31, R-10).

Los fallos se cuentan en memoria por pareja `(client_ip, email)` en una ventana fija: empieza
en el primer fallo y dura `LOGIN_WINDOW_MINUTES`. Al llegar a `LOGIN_MAX_ATTEMPTS` fallos, la
pareja queda bloqueada hasta que acaba la ventana. Un login correcto borra el contador.
"""

import logging
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from cachetools import TTLCache

from app.config import settings
from app.core.exceptions import TooManyRequestsError
from app.services.user_service import normalize_email

logger = logging.getLogger(__name__)

TOO_MANY_ATTEMPTS_CODE = "too_many_attempts"
TOO_MANY_ATTEMPTS_DETAIL = "Too many failed login attempts. Try again later."
MAX_TRACKED_KEYS = 10_000


@dataclass
class _Attempts:
    count: int
    first_failure: float


class LoginRateLimiter:
    """Cuenta los fallos de login por `(client_ip, email)` en una ventana fija."""

    def __init__(
        self,
        max_attempts: int,
        window_seconds: int,
        timer: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._timer = timer
        self._attempts: TTLCache[tuple[str, str], _Attempts] = TTLCache(
            maxsize=MAX_TRACKED_KEYS, ttl=window_seconds, timer=timer
        )
        self._lock = threading.Lock()

    def check(self, client_ip: str, email: str) -> None:
        """Lanza `TooManyRequestsError` si la pareja está bloqueada; si no, no hace nada."""
        retry_after = self.retry_after(client_ip, email)
        if retry_after is not None:
            raise TooManyRequestsError(
                TOO_MANY_ATTEMPTS_DETAIL, retry_after=retry_after, code=TOO_MANY_ATTEMPTS_CODE
            )

    def retry_after(self, client_ip: str, email: str) -> int | None:
        """Segundos que faltan para que acabe el bloqueo, o `None` si no está bloqueada."""
        with self._lock:
            attempts = self._attempts.get(_key(client_ip, email))
            if attempts is None or attempts.count < self.max_attempts:
                return None
            remaining = self.window_seconds - (self._timer() - attempts.first_failure)
        return max(1, math.ceil(remaining))

    def register_failure(self, client_ip: str, email: str) -> None:
        """Suma un fallo. La ventana no se alarga: la marca el primer fallo."""
        key = _key(client_ip, email)
        with self._lock:
            attempts = self._attempts.get(key)
            if attempts is None:
                attempts = _Attempts(count=0, first_failure=self._timer())
                self._attempts[key] = attempts
            attempts.count += 1
            just_blocked = attempts.count == self.max_attempts
        if just_blocked:
            logger.warning("Login blocked", extra={"client_ip": key[0], "email": key[1]})

    def reset(self, client_ip: str, email: str) -> None:
        """Borra los fallos de la pareja tras un login correcto."""
        with self._lock:
            self._attempts.pop(_key(client_ip, email), None)

    def clear(self) -> None:
        """Borra todos los contadores (lo usan los tests)."""
        with self._lock:
            self._attempts.clear()


def _key(client_ip: str, email: str) -> tuple[str, str]:
    return client_ip, normalize_email(email)


login_rate_limiter = LoginRateLimiter(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    window_seconds=settings.LOGIN_WINDOW_MINUTES * 60,
)
