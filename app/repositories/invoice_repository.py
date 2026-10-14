from datetime import date, datetime, time, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.model_invoice import Invoice


def get_by_id(db: Session, invoice_id: int) -> Invoice | None:
    return db.get(Invoice, invoice_id)


def max_sequence(db: Session, year: int) -> int | None:
    return db.scalar(select(func.max(Invoice.sequence)).where(Invoice.year == year))


def list_query(date_from: date | None = None, date_to: date | None = None) -> Select:
    """Facturas ordenadas por número, filtradas por fecha de emisión (ambas incluidas)."""
    stmt = select(Invoice)
    if date_from is not None:
        stmt = stmt.where(Invoice.issued_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        next_day = datetime.combine(date_to + timedelta(days=1), time.min)
        stmt = stmt.where(Invoice.issued_at < next_day)
    return stmt.order_by(Invoice.year, Invoice.sequence)


def list_with_orders(
    db: Session, date_from: date | None = None, date_to: date | None = None
) -> list[Invoice]:
    stmt = list_query(date_from, date_to).options(selectinload(Invoice.order))
    return list(db.scalars(stmt).all())


def add(db: Session, invoice: Invoice) -> Invoice:
    db.add(invoice)
    return invoice
