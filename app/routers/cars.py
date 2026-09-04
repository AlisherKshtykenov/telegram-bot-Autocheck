"""GET-эндпоинт для фронтенда: список загруженных машин."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Car
from app.schemas import CarOut

router = APIRouter(prefix="/cars", tags=["cars"])


@router.get("", response_model=list[CarOut])
def list_cars(limit: int = 100, db: Session = Depends(get_db)) -> list[Car]:
    return db.query(Car).order_by(desc(Car.updated_at)).limit(limit).all()