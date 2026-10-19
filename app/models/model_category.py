import enum

from sqlalchemy import Column, Integer, String

from app.database import Base


class Station(str, enum.Enum):
    kitchen = "kitchen"
    bar = "bar"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    station = Column(
        String(10),
        nullable=False,
        default=Station.kitchen.value,
        server_default=Station.kitchen.value,
    )
