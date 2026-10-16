"""Lógica de negocio de reservas (HU-10): solapamientos, aforo y estados.

Reglas:
- Dos reservas activas (status != cancelled) de la misma mesa no pueden
  solaparse: [a_start, a_end) y [b_start, b_end) se solapan si
  a_start < b_end AND b_start < a_end.
- party_size <= dining_tables.capacity.

Los permisos (quién puede tocar qué reserva) se comprueban en el router.
"""

import logging
from datetime import date, datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

from sqlalchemy import Select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ReservationConflict,
    UnprocessableError,
)
from app.models.dining_table import DiningTable
from app.models.model_user import User
from app.models.reservation import CANCELLED, CONFIRMED, Reservation
from app.repositories import (
    dining_table_repository,
    reservation_repository,
    user_repository,
)
from app.repositories.reservation_repository import find_overlapping
from app.schemas.reservation import (
    MAX_CUSTOMER_PARTY_SIZE,
    ReservationCreate,
    ReservationUpdate,
)

logger = logging.getLogger(__name__)

CANDIDATE_TABLES_LIMIT = 100


def get_reservation(db: Session, reservation_id: int) -> Reservation:
    reservation = reservation_repository.get_by_id(db, reservation_id)
    if reservation is None:
        logger.warning("Reserva id=%s no encontrada", reservation_id)
        raise NotFoundError(
            f"La reserva {reservation_id} no existe", code="reservation_not_found"
        )
    return reservation


def list_reservations_query(
    *,
    status: str | None = None,
    table_id: int | None = None,
    day: date | None = None,
    user_id: int | None = None,
) -> Select[tuple[Reservation]]:
    """Select de reservas filtrado y ordenado por fecha (se pagina en el router)."""
    return reservation_repository.list_query(
        status=status, table_id=table_id, day=day, user_id=user_id
    )


def _get_table_for_update(db: Session, table_id: int) -> DiningTable:
    """Carga la mesa bloqueando su fila (FOR UPDATE en Postgres).

    El bloqueo serializa las reservas concurrentes de una misma mesa, para que
    dos peticiones simultáneas no pasen a la vez la comprobación de solapamiento.
    """
    table = dining_table_repository.get_by_id_for_update(db, table_id)
    if table is None:
        logger.warning("Mesa id=%s no encontrada al reservar", table_id)
        raise NotFoundError(f"La mesa {table_id} no existe", code="table_not_found")
    return table


def _ensure_capacity(table: DiningTable, party_size: int) -> None:
    if party_size > table.capacity:
        raise UnprocessableError(
            f"La mesa {table.number} admite {table.capacity} personas "
            f"y la reserva es para {party_size}",
            code="party_size_exceeds_capacity",
        )


def _ensure_no_overlap(
    db: Session,
    *,
    table_id: int,
    reserved_at: datetime,
    duration_min: int,
    exclude_id: int | None = None,
) -> None:
    clash = find_overlapping(
        db,
        table_id=table_id,
        reserved_at=reserved_at,
        duration_min=duration_min,
        exclude_id=exclude_id,
    )
    if clash is not None:
        logger.info(
            "Solapamiento en mesa id=%s: %s (+%s min) choca con la reserva id=%s",
            table_id,
            reserved_at,
            duration_min,
            clash.id,
        )
        raise ReservationConflict(
            f"La mesa ya está reservada de {clash.reserved_at:%H:%M} a "
            f"{clash.reserved_at + timedelta(minutes=clash.duration_min):%H:%M} "
            f"del {clash.reserved_at:%d/%m/%Y}"
        )


def _ensure_customer_party_size(party_size: int) -> None:
    if party_size > MAX_CUSTOMER_PARTY_SIZE:
        raise UnprocessableError(
            f"Para reservas de más de {MAX_CUSTOMER_PARTY_SIZE} personas, "
            "llama al restaurante",
            code="party_size_too_large",
        )


def _restaurant_now() -> datetime:
    """Hora actual del restaurante sin zona, como se guarda `reserved_at`."""
    return datetime.now(ZoneInfo(settings.RESTAURANT_TIMEZONE)).replace(tzinfo=None)


def _ensure_not_in_past(reserved_at: datetime) -> None:
    if reserved_at < _restaurant_now():
        raise UnprocessableError(
            "No se puede reservar en una fecha pasada", code="reservation_in_past"
        )


def _assign_table(db: Session, data: ReservationCreate) -> DiningTable:
    """Bloquea y devuelve la mesa libre más pequeña con sitio para la reserva.

    Si otra petición ocupa una candidata entre medias se prueba la siguiente.
    """
    candidates, _ = dining_table_repository.list_available_page(
        db,
        starts_at=data.reserved_at,
        ends_at=data.reserved_at + timedelta(minutes=data.duration_min),
        party_size=data.party_size,
        skip=0,
        limit=CANDIDATE_TABLES_LIMIT,
    )
    for candidate in candidates:
        table = _get_table_for_update(db, candidate.id)
        try:
            _ensure_no_overlap(
                db,
                table_id=table.id,
                reserved_at=data.reserved_at,
                duration_min=data.duration_min,
            )
        except ReservationConflict:
            continue
        return table
    logger.info(
        "Sin mesa libre para %s personas el %s", data.party_size, data.reserved_at
    )
    raise ConflictError(
        f"No hay mesa libre para {data.party_size} personas el "
        f"{data.reserved_at:%d/%m/%Y} a las {data.reserved_at:%H:%M}",
        code="no_table_available",
    )


def ensure_user_exists(db: Session, user_id: int) -> User:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise NotFoundError(f"El usuario {user_id} no existe", code="user_not_found")
    return user


def create_reservation(
    db: Session, data: ReservationCreate, user_id: int, *, is_customer: bool = False
) -> Reservation:
    """Crea una reserva confirmada para `user_id` validando aforo y solapamiento.

    Sin `table_id` asigna la mesa libre más pequeña con sitio. Un customer no puede
    reservar para más de MAX_CUSTOMER_PARTY_SIZE personas.
    """
    if is_customer:
        _ensure_customer_party_size(data.party_size)
    try:
        if data.table_id is None:
            _ensure_not_in_past(data.reserved_at)
            table = _assign_table(db, data)
            _ensure_capacity(table, data.party_size)
        else:
            table = _get_table_for_update(db, data.table_id)
            _ensure_capacity(table, data.party_size)
            _ensure_no_overlap(
                db,
                table_id=table.id,
                reserved_at=data.reserved_at,
                duration_min=data.duration_min,
            )
        reservation = Reservation(
            **data.model_dump(exclude={"user_id", "table_id"}),
            table_id=table.id,
            user_id=user_id,
            status=CONFIRMED,
        )
        reservation_repository.add(db, reservation)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(reservation)
    logger.info(
        "Reserva creada id=%s mesa=%s usuario=%s",
        reservation.id,
        reservation.table_id,
        user_id,
    )
    return reservation


def update_reservation(
    db: Session,
    reservation: Reservation,
    data: ReservationUpdate,
    *,
    is_customer: bool = False,
) -> Reservation:
    """Aplica una edición parcial y revalida aforo y solapamiento si hace falta."""
    changes = data.model_dump(exclude_unset=True)
    if is_customer and "party_size" in changes:
        _ensure_customer_party_size(changes["party_size"])
    try:
        table_id = changes.get("table_id", reservation.table_id)
        party_size = changes.get("party_size", reservation.party_size)
        reserved_at = changes.get("reserved_at", reservation.reserved_at)
        duration_min = changes.get("duration_min", reservation.duration_min)
        status = changes.get("status", reservation.status)

        check_capacity = bool({"table_id", "party_size"} & changes.keys())
        check_overlap = status != CANCELLED and (
            bool({"table_id", "reserved_at", "duration_min"} & changes.keys())
            or reservation.status == CANCELLED
        )
        if check_capacity or check_overlap:
            table = _get_table_for_update(db, table_id)
        if check_capacity:
            _ensure_capacity(table, party_size)
        if check_overlap:
            _ensure_no_overlap(
                db,
                table_id=table_id,
                reserved_at=reserved_at,
                duration_min=duration_min,
                exclude_id=reservation.id,
            )

        for field, value in changes.items():
            setattr(reservation, field, value)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(reservation)
    logger.info("Reserva id=%s editada: %s", reservation.id, sorted(changes))
    return reservation


def cancel_reservation(db: Session, reservation: Reservation) -> Reservation:
    """Cancela una reserva confirmada. Libera el hueco para otras reservas."""
    if reservation.status != CONFIRMED:
        raise ConflictError(
            f"Solo se pueden cancelar reservas confirmadas "
            f"(estado actual: {reservation.status})",
            code="reservation_not_cancellable",
        )
    reservation.status = CANCELLED
    db.commit()
    db.refresh(reservation)
    logger.info("Reserva id=%s cancelada", reservation.id)
    return reservation


def delete_reservation(db: Session, reservation: Reservation) -> None:
    reservation_id = reservation.id
    reservation_repository.delete(db, reservation)
    db.commit()
    logger.info("Reserva id=%s borrada", reservation_id)


def confirmation_email(
    db: Session, reservation: Reservation
) -> tuple[str, str, str] | None:
    """(to, subject, html) del email de confirmación, o None si no hay destinatario."""
    user = user_repository.get_by_id(db, reservation.user_id)
    if user is None or not user.email:
        return None
    table = dining_table_repository.get_by_id(db, reservation.table_id)
    table_label = f"mesa {table.number}" if table else f"mesa {reservation.table_id}"
    subject = "Tu reserva está confirmada"
    html = (
        f"<p>Hola {escape(user.name)}:</p>"
        f"<p>Tu reserva del <strong>{reservation.reserved_at:%d/%m/%Y}</strong> a las "
        f"<strong>{reservation.reserved_at:%H:%M}</strong> ({escape(table_label)}, "
        f"{reservation.party_size} personas) está confirmada.</p>"
        "<p>RestoAPI</p>"
    )
    return user.email, subject, html


def cancellation_email(
    db: Session, reservation: Reservation
) -> tuple[str, str, str] | None:
    """(to, subject, html) del email de cancelación, o None si no hay destinatario."""
    user = user_repository.get_by_id(db, reservation.user_id)
    if user is None or not user.email:
        return None
    table = dining_table_repository.get_by_id(db, reservation.table_id)
    table_label = f"mesa {table.number}" if table else f"mesa {reservation.table_id}"
    subject = "Tu reserva ha sido cancelada"
    html = (
        f"<p>Hola {escape(user.name)}:</p>"
        f"<p>Tu reserva del <strong>{reservation.reserved_at:%d/%m/%Y}</strong> a las "
        f"<strong>{reservation.reserved_at:%H:%M}</strong> ({escape(table_label)}, "
        f"{reservation.party_size} personas) ha sido cancelada.</p>"
        "<p>RestoAPI</p>"
    )
    return user.email, subject, html
