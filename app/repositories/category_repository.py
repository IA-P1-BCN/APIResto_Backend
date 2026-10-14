from sqlalchemy.orm import Session

from app.models.model_category import Category
from app.models.model_dish import Dish


def get_by_id(db: Session, category_id: int) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


def get_by_name(db: Session, name: str) -> Category | None:
    return db.query(Category).filter(Category.name == name).first()


def list_categories(db: Session) -> list[Category]:
    return db.query(Category).order_by(Category.sort_order, Category.name).all()


def has_dishes(db: Session, category_id: int) -> bool:
    return db.query(Dish).filter(Dish.category_id == category_id).first() is not None


def add(db: Session, category: Category) -> Category:
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def save(db: Session, category: Category) -> Category:
    db.commit()
    db.refresh(category)
    return category


def delete(db: Session, category: Category) -> None:
    db.delete(category)
    db.commit()
