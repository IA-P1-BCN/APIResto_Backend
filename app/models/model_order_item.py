from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.model_category import Station


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    dish_id = Column(Integer, ForeignKey("dishes.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(8, 2), nullable=False)
    notes = Column(String(255))
    prepared_quantity = Column(Integer, nullable=False, default=0, server_default="0")
    served_quantity = Column(Integer, nullable=False, default=0, server_default="0")

    dish = relationship("Dish")

    @property
    def station(self) -> str:
        """Estación de la línea: la de la categoría de su plato (R-14)."""
        category = self.dish.category if self.dish else None
        return category.station if category else Station.kitchen.value

    @property
    def prepared(self) -> bool:
        return self.prepared_quantity >= self.quantity

    @property
    def served(self) -> bool:
        return self.served_quantity >= self.quantity

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_quantity_positive"),
    )