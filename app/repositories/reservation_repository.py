from datetime import date, datetime, time, timedelta

from sqlalchemy import DateTime, Select, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import FunctionElement

from app.models.reservation import CANCELLED, Reservation


class reservation_end(FunctionElement):
    """Expresión SQL `reserved_at + duration_min minutos`, según el dialecto."""

    type = DateTime()
    inherit_cache = True
    name = "reservation_end"


@compiles(reservation_end)
def _reservation_end_postgres(element, compiler, **kw) -> str:
    start, minutes = (compiler.process(arg, **kw) for arg in element.clauses)
    return f"({start} + make_interval(mins => {minutes}))"


@compiles(reservation_end, "sqlite")
def _reservation_end_sqlite(element, compiler, **kw) -> str:
    start, minutes = (compiler.process(arg, **kw) for arg in element.clauses)
    return (
        f"(strftime('%Y-%m-%d %H:%M:%f', {start}, '+' || {minutes} || ' minutes')"
        " || '000')"
    )


def get_by_id(db: Session, reservation_id: int) -> Reservation | None:
    return db.get(Reservation, reservation_id)


def list_query(
    *,
    status: str | None = None,
    table_id: int | None = None,
    day: date | None = None,
    user_id: int | None = None,
) -> Select[tuple[Reservation]]:
    """Select de reservas filtrado y ordenado por fecha (se pagina en el router)."""
    stmt = select(Reservation).order_by(Reservation.reserved_at, Reservation.id)
    if status is not None:
        stmt = stmt.where(Reservation.status == status)
    if table_id is not None:
        stmt = stmt.where(Reservation.table_id == table_id)
    if user_id is not None:
        stmt = stmt.where(Reservation.user_id == user_id)
    if day is not None:
        start = datetime.combine(day, time.min)
        stmt = stmt.where(
            Reservation.reserved_at >= start,
            Reservation.reserved_at < start + timedelta(days=1),
        )
    return stmt


def find_overlapping(
    db: Session,
    *,
    table_id: int,
    reserved_at: datetime,
    duration_min: int,
    exclude_id: int | None = None,
) -> Reservation | None:
    """Primera reserva activa de la mesa que se solapa con el intervalo dado."""
    ends_at = reserved_at + timedelta(minutes=duration_min)
    stmt = (
        select(Reservation)
        .where(
            Reservation.table_id == table_id,
            Reservation.status != CANCELLED,
            Reservation.reserved_at < ends_at,
            reservation_end(Reservation.reserved_at, Reservation.duration_min)
            > reserved_at,
        )
        .order_by(Reservation.reserved_at)
        .limit(1)
    )
    if exclude_id is not None:
        stmt = stmt.where(Reservation.id != exclude_id)
    return db.scalar(stmt)


def exists_for_table(db: Session, table_id: int) -> bool:
    return (
        db.scalar(select(Reservation.id).where(Reservation.table_id == table_id).limit(1))
        is not None
    )


def add(db: Session, reservation: Reservation) -> Reservation:
    db.add(reservation)
    return reservation


def delete(db: Session, reservation: Reservation) -> None:
    db.delete(reservation)
