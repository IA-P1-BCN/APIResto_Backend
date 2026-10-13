"""Estadísticas de ventas y platos más vendidos (HU-15).

Cuenta como venta todo pedido en estado `served` o `paid`. Los `pending` e
`in_kitchen` todavía no son venta y los `cancelled` no lo son nunca.

Las fechas `date_from` y `date_to` filtran por la fecha de creación del pedido y
las dos están incluidas.

Caché: cada resultado se guarda `STATS_CACHE_TTL` segundos (60 por defecto) en
memoria, con una entrada por combinación de parámetros. Durante ese tiempo las
ventas nuevas no se ven. Con `STATS_CACHE_TTL=0` no se guarda nada.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from threading import Lock

from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from sqlalchemy.orm import Session

from app.config import settings
from app.repositories import stats_repository

CENT = Decimal("0.01")
ZERO = Decimal("0.00")

_sales_cache: TTLCache = TTLCache(maxsize=128, ttl=settings.STATS_CACHE_TTL)
_top_dishes_cache: TTLCache = TTLCache(
    maxsize=128, ttl=settings.STATS_CACHE_TTL)
_cache_lock = Lock()


def clear_cache() -> None:
    """Vacía las cachés de estadísticas (la usan los tests)."""
    with _cache_lock:
        _sales_cache.clear()
        _top_dishes_cache.clear()


@dataclass(frozen=True)
class SalesDay:
    day: date
    orders_count: int
    total_sales: Decimal


@dataclass(frozen=True)
class SalesSummary:
    date_from: date | None
    date_to: date | None
    orders_count: int
    total_sales: Decimal
    average_ticket: Decimal
    daily: tuple[SalesDay, ...]


@dataclass(frozen=True)
class TopDish:
    dish_id: int
    name: str
    quantity: int
    revenue: Decimal


def _money(value: object) -> Decimal:
    """Importe con 2 decimales. SUM devuelve None si no hay filas."""
    return Decimal(str(value or 0)).quantize(CENT)


def _as_date(value: object) -> date:
    """func.date() devuelve un date en Postgres y un texto 'YYYY-MM-DD' en SQLite."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


@cached(
    _sales_cache,
    key=lambda db, date_from=None, date_to=None: hashkey(date_from, date_to),
    lock=_cache_lock,
)
def sales_summary(
    db: Session, date_from: date | None = None, date_to: date | None = None
) -> SalesSummary:
    """Número de pedidos, total vendido, ticket medio y desglose por día."""
    rows = stats_repository.sales_by_day(db, date_from, date_to)

    daily = tuple(
        SalesDay(day=_as_date(d), orders_count=count,
                 total_sales=_money(total))
        for d, count, total in rows
    )
    orders_count = sum(d.orders_count for d in daily)
    total_sales = sum((d.total_sales for d in daily), ZERO)
    average_ticket = (
        total_sales / orders_count).quantize(CENT) if orders_count else ZERO
    return SalesSummary(
        date_from=date_from,
        date_to=date_to,
        orders_count=orders_count,
        total_sales=total_sales,
        average_ticket=average_ticket,
        daily=daily,
    )


@cached(
    _top_dishes_cache,
    key=lambda db, date_from=None, date_to=None, limit=5: hashkey(
        date_from, date_to, limit
    ),
    lock=_cache_lock,
)
def top_dishes(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 5,
) -> tuple[TopDish, ...]:
    """Platos más vendidos por unidades. Empate: más ingresos y luego menor id."""
    return tuple(
        TopDish(dish_id=dish_id, name=name,
                quantity=int(qty), revenue=_money(rev))
        for dish_id, name, qty, rev in stats_repository.top_dishes_rows(
            db, date_from, date_to, limit
        )
    )
