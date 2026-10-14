from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.model_category import Category
from app.repositories import category_repository
from app.schemas.schema_category import CategoryCreate, CategoryUpdate


def get_category(db: Session, category_id: int) -> Category:
    """Return the category or raise NotFoundError (404)."""
    category = category_repository.get_by_id(db, category_id)
    if not category:
        raise NotFoundError("Category not found")
    return category


def list_categories(db: Session) -> list[Category]:
    return category_repository.list_categories(db)


def create_category(db: Session, data: CategoryCreate) -> Category:
    if category_repository.get_by_name(db, data.name):
        raise ConflictError("Category already exists")

    return category_repository.add(db, Category(**data.model_dump()))


def update_category(db: Session, category_id: int, data: CategoryUpdate) -> Category:
    category = get_category(db, category_id)

    if (
        data.name
        and data.name != category.name
        and category_repository.get_by_name(db, data.name)
    ):
        raise ConflictError("Category already exists")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    return category_repository.save(db, category)


def delete_category(db: Session, category_id: int) -> None:
    category = get_category(db, category_id)

    if category_repository.has_dishes(db, category_id):
        raise ConflictError("Category has dishes and cannot be deleted")

    category_repository.delete(db, category)
