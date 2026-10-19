"""Crea el primer admin (sin él nadie puede usar /users).

    python -m app.scripts.create_admin EMAIL PASSWORD [NOMBRE]
    docker compose exec api python -m app.scripts.create_admin EMAIL PASSWORD [NOMBRE]
"""
import sys

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models.model_user import Role, User
from app.repositories import user_repository


def create_admin(db: Session, email: str, password: str, name: str = "Admin") -> User:
    """Crea o promueve el admin; nace con el email verificado (R-15, decisión P2)."""
    user = user_repository.get_by_email(db, email)
    if user is None:
        user = User(name=name, email=email, password_hash=hash_password(password))
        db.add(user)
    user.role = Role.admin.value
    user.is_active = True
    user.email_verified = True
    db.commit()
    db.refresh(user)
    return user


def main(argv: list[str]) -> None:
    if len(argv) not in (2, 3):
        sys.exit("Uso: python -m app.scripts.create_admin EMAIL PASSWORD [NOMBRE]")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = create_admin(db, *argv)
        print(f"Admin listo: {user.email} (id {user.id})")


if __name__ == "__main__":
    main(sys.argv[1:])
