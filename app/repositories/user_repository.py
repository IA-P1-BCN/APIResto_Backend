from sqlalchemy.orm import Session

from app.models.model_user import User


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def list_users(
    db: Session, skip: int = 0, limit: int = 100, include_deleted: bool = False
) -> list[User]:
    query = db.query(User)
    if not include_deleted:
        query = query.filter(User.deleted_at.is_(None))
    return query.order_by(User.id).offset(skip).limit(limit).all()


def add(db: Session, user: User) -> User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def save(db: Session, user: User) -> User:
    db.commit()
    db.refresh(user)
    return user
