from datetime import datetime

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.models.dining_table import OUT_OF_SERVICE, DiningTable
from app.models.reservation import CANCELLED, Reservation
from app.repositories.reservation_repository import reservation_end


def get_by_id(db: Session, table_id: int) -> DiningTable | None:
    return db.get(DiningTable, table_id)


def get_by_id_for_update(db: Session, table_id: int) -> DiningTable | None:
    """Carga la mesa bloqueando su fila (FOR UPDATE en Postgres)."""
    return db.scalar(
        select(DiningTable).where(DiningTable.id == table_id).with_for_update()
    )


def find_id_by_number(
    db: Session, number: int, exclude_id: int | None = None
) -> int | None:
    query = select(DiningTable.id).where(DiningTable.number == number)
    if exclude_id is not None:
        query = query.where(DiningTable.id != exclude_id)
    return db.scalar(query)


def list_page(db: Session, skip: int, limit: int) -> tuple[list[DiningTable], int]:
    total = db.scalar(select(func.count()).select_from(DiningTable)) or 0
    items = db.scalars(
        select(DiningTable).order_by(DiningTable.id).offset(skip).limit(limit)
    ).all()
    return list(items), total


def list_available_page(
    db: Session,
    *,
    starts_at: datetime,
    ends_at: datetime,
    party_size: int,
    skip: int,
    limit: int,
) -> tuple[list[DiningTable], int]:
    overlapping = exists().where(
        Reservation.table_id == DiningTable.id,
        Reservation.status != CANCELLED,
        Reservation.reserved_at < ends_at,
        reservation_end(Reservation.reserved_at, Reservation.duration_min) > starts_at,
    )
    query = select(DiningTable).where(
        DiningTable.capacity >= party_size,
        DiningTable.status != OUT_OF_SERVICE,
        ~overlapping,
    )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(DiningTable.capacity, DiningTable.number)
        .offset(skip)
        .limit(limit)
    ).all()
    return list(items), total


def add(db: Session, table: DiningTable) -> DiningTable:
    db.add(table)
    db.flush()
    return table


def flush(db: Session) -> None:
    db.flush()


def delete(db: Session, table: DiningTable) -> None:
    db.delete(table)
    db.flush()
