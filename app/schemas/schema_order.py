from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class OrderItemCreate(BaseModel):
    dish_id: int
    quantity: int
    notes: str | None = None

class OrderCreate(BaseModel):
    table_id: int
    items: list[OrderItemCreate]

class OrderItemOut(BaseModel):
    id: int
    dish_id: int
    quantity: int
    unit_price: Decimal
    notes: str | None = None
    prepared: bool = False
    served: bool = False

    class Config:
        from_attributes = True

class OrderItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prepared: bool | None = None
    served: bool | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "OrderItemUpdate":
        if self.prepared is None and self.served is None:
            raise ValueError("Indica prepared, served o los dos")
        return self


class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "in_kitchen", "served", "paid", "cancelled"]


class OrderOut(BaseModel):
    id: int
    table_id: int
    waiter_id: int | None = None
    status: str
    total: Decimal
    created_at: datetime
    updated_at: datetime | None = None
    items: list[OrderItemOut]

    class Config:
        from_attributes = True