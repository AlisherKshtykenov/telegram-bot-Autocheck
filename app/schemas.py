from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CarOut(BaseModel):
    """То, что отдаём наружу через API — отдельно от ORM-модели Car."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vin: str
    brand: str
    model: str
    year: int
    mileage: int
    defects: str
    dealer: str
    price: float
    created_at: datetime
    updated_at: datetime


class UploadResult(BaseModel):
    """Ответ на загрузку файла — сколько добавили/обновили."""

    inserted: int
    updated: int
    total_rows: int