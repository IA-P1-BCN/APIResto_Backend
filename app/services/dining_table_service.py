"""
Business logic for dining tables (HU-09).

Assumptions: see PENDING-CONTRACTS.md (E1 for exceptions, P1 for
pagination).
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.dining_table import DiningTable
from app.models.reservation import DEFAULT_DURATION_MIN
from app.repositories import (
    dining_table_repository,
    order_repository,
    reservation_repository,
)
from app.schemas.dining_table import DiningTableCreate, DiningTableUpdate

logger = logging.getLogger(__name__)

CONFLICT_CODE = "conflict"
TABLE_IN_USE_CODE = "table_in_use"
NOT_FOUND_CODE = "not_found"

def _ensure_number_available(
    db: Session, number: int, exclude_id: int | None = None
) -> None:
    """Raise ConflictError if another table already uses `number`."""
    existing_id = dining_table_repository.find_id_by_number(db, number, exclude_id)
    if existing_id is not None:
        logger.warning(
            "Table number %s already taken by table id=%s", number, existing_id
        )
        raise ConflictError(f"Table number {number} already exists", code=CONFLICT_CODE)


def list_tables(
    db: Session, skip: int = 0, limit: int = 100
) -> tuple[list[DiningTable], int]:
    """Return a page of tables ordered by id, plus the total count."""
    return dining_table_repository.list_page(db, skip, limit)


def get_table(db: Session, table_id: int) -> DiningTable:
    """Return the table with `table_id` or raise NotFoundError."""
    table = dining_table_repository.get_by_id(db, table_id)
    if table is None:
        logger.warning("Table id=%s not found", table_id)
        raise NotFoundError(f"Table {table_id} not found", code=NOT_FOUND_CODE)
    return table


def create_table(db: Session, data: DiningTableCreate) -> DiningTable:
    """Create a table. Raise ConflictError if `number` is already in use."""
    _ensure_number_available(db, data.number)
    table = dining_table_repository.add(db, DiningTable(**data.model_dump()))
    logger.info("Created table id=%s number=%s", table.id, table.number)
    return table


def update_table(db: Session, table_id: int, data: DiningTableUpdate) -> DiningTable:
    """Replace every field of a table (PUT semantics)."""
    table = get_table(db, table_id)
    _ensure_number_available(db, data.number, exclude_id=table_id)
    for field, value in data.model_dump().items():
        setattr(table, field, value)
    dining_table_repository.flush(db)
    logger.info("Updated table id=%s", table_id)
    return table


def change_status(db: Session, table_id: int, status: str) -> DiningTable:
    """Change only the status of a table.

    `status` is expected to be validated by the caller (DiningTableStatusUpdate).
    """
    table = get_table(db, table_id)
    previous = table.status
    table.status = status
    dining_table_repository.flush(db)
    logger.info("Changed status of table id=%s: %s -> %s", table_id, previous, status)
    return table


def delete_table(db: Session, table_id: int) -> None:
    """Delete a table. Raise NotFoundError if it does not exist.

    Raise ConflictError with code "table_in_use" if any order or reservation
    still references the table: deleting would violate their foreign keys and
    Postgres would raise IntegrityError, which the API would surface as a
    generic 500. We check first so the client gets a clear 409.

    Flushes after the delete so later lookups in the same session (e.g.
    get_table) no longer find it. The commit is left to the caller.
    """
    table = get_table(db, table_id)

    if order_repository.exists_for_table(db, table_id):
        logger.warning("Cannot delete table id=%s: has orders", table_id)
        raise ConflictError(
            f"Table {table_id} has orders and cannot be deleted",
            code=TABLE_IN_USE_CODE,
        )

    if reservation_repository.exists_for_table(db, table_id):
        logger.warning("Cannot delete table id=%s: has reservations", table_id)
        raise ConflictError(
            f"Table {table_id} has reservations and cannot be deleted",
            code=TABLE_IN_USE_CODE,
        )

    dining_table_repository.delete(db, table)
    logger.info("Deleted table id=%s", table_id)


def list_available_tables(
    db: Session,
    *,
    reserved_at: datetime,
    party_size: int,
    duration_min: int = DEFAULT_DURATION_MIN,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[DiningTable], int]:
    """Return a page of tables free for `party_size` guests in the given slot (HU-18).

    A table is available when it seats at least `party_size`, it is not
    out of service and no active reservation (status != cancelled) overlaps
    the half-open interval [reserved_at, reserved_at + duration_min), the
    same rule used to reject overlapping reservations (HU-10).
    Tables are ordered by capacity and number, so the best fit comes first.
    """
    if reserved_at.tzinfo is not None:
        reserved_at = reserved_at.astimezone(UTC).replace(tzinfo=None)
    ends_at = reserved_at + timedelta(minutes=duration_min)

    items, total = dining_table_repository.list_available_page(
        db,
        starts_at=reserved_at,
        ends_at=ends_at,
        party_size=party_size,
        skip=skip,
        limit=limit,
    )
    logger.info(
        "Available tables at %s (+%s min) for %s guests: %s",
        reserved_at,
        duration_min,
        party_size,
        total,
    )
    return items, total
