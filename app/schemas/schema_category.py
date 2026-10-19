from pydantic import BaseModel, ConfigDict, Field

from app.models.model_category import Station


class CategoryBase(BaseModel):
    name: str = Field(max_length=50)
    sort_order: int = 0
    station: Station = Station.kitchen


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    sort_order: int | None = None
    station: Station | None = None


class CategoryOut(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
