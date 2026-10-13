from sqlalchemy.orm import Session

from app.models.dining_table import DiningTable


def get_by_id(db: Session, table_id: int) -> DiningTable | None:
    return db.get(DiningTable, table_id)
