"""Webhook/API-триггер: принудительная загрузка файла через HTTP POST."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import UploadResult
from app.services.parser import import_file

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=UploadResult)
async def upload_dataset(file: UploadFile, db: Session = Depends(get_db)) -> UploadResult:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Поддерживаются только CSV-файлы")

    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    dest_path = settings.uploads_dir / file.filename
    with dest_path.open("wb") as f:
        f.write(await file.read())

    try:
        stats = import_file(db, dest_path, source_name=f"api:{file.filename}")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return UploadResult(inserted=stats.inserted, updated=stats.updated, total_rows=stats.total_rows)