from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.model_category import Station

ProgressStage = Literal["waiting", "preparing", "ready_to_serve", "all_served"]


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
    prepared_quantity: int = 0
    served_quantity: int = 0
    prepared: bool = False
    served: bool = False
    station: str = "kitchen"

    class Config:
        from_attributes = True

    @computed_field
    @property
    def ready_to_serve(self) -> int:
        """Unidades preparadas que aún no se han servido; nunca menos de 0 (R-16)."""
        return max(self.prepared_quantity - self.served_quantity, 0)


def _stage(quantity: int, prepared: int, served: int, ready: int) -> ProgressStage:
    """Resumen del progreso (R-16): gana la primera condición que se cumple."""
    if quantity and served >= quantity:
        return "all_served"
    if ready > 0:
        return "ready_to_serve"
    if prepared == 0 and served == 0:
        return "waiting"
    return "preparing"


class StationProgress(BaseModel):
    quantity: int
    prepared_quantity: int
    served_quantity: int
    ready_to_serve: int
    stage: ProgressStage

    @classmethod
    def from_items(cls, items: list[OrderItemOut]) -> "StationProgress":
        """Suma las unidades de las líneas y calcula su `stage`."""
        quantity = sum(item.quantity for item in items)
        prepared = sum(item.prepared_quantity for item in items)
        served = sum(item.served_quantity for item in items)
        ready = sum(item.ready_to_serve for item in items)
        return cls(
            quantity=quantity,
            prepared_quantity=prepared,
            served_quantity=served,
            ready_to_serve=ready,
            stage=_stage(quantity, prepared, served, ready),
        )


class OrderProgress(StationProgress):
    by_station: dict[str, StationProgress] = Field(default_factory=dict)


class OrderItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prepared: bool | None = None
    served: bool | None = None
    prepared_quantity: int | None = Field(default=None, ge=0)
    served_quantity: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _at_least_one(self) -> "OrderItemUpdate":
        if self.prepared is not None and self.prepared_quantity is not None:
            raise ValueError("Indica prepared o prepared_quantity, no los dos")
        if self.served is not None and self.served_quantity is not None:
            raise ValueError("Indica served o served_quantity, no los dos")
        if all(
            value is None
            for value in (self.prepared, self.served, self.prepared_quantity, self.served_quantity)
        ):
            raise ValueError("Indica prepared, served, prepared_quantity o served_quantity")
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

    @computed_field
    @property
    def progress(self) -> OrderProgress:
        """Progreso de las líneas de la respuesta, total y por estación (R-16)."""
        by_station = {
            station.value: StationProgress.from_items(lines)
            for station in Station
            if (lines := [item for item in self.items if item.station == station.value])
        }
        total = StationProgress.from_items(self.items)
        return OrderProgress(**total.model_dump(), by_station=by_station)