"""
Парсер файла выгрузки (CSV) + upsert в БД по VIN.

upsert = "update or insert": если машина с таким VIN уже в базе — обновляем
её поля, если нет — создаём новую запись. Так повторная загрузка того же
файла не создаёт дублей.

preview_file() делает ту же проверку, но БЕЗ записи в базу — только читает
и считает, что бы произошло. Используется, чтобы показать клиенту
статистику перед подтверждением загрузки (см. app/telegram_bot.py).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Car

REQUIRED_COLUMNS = {"vin", "brand", "model", "year", "mileage", "defects", "dealer", "price"}


@dataclass
class ImportStats:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    total_rows: int = 0


@dataclass
class PreviewStats:
    total_rows: int = 0
    new_count: int = 0
    update_count: int = 0
    invalid_count: int = 0
    duplicate_in_file: int = 0
    warnings: list[str] = field(default_factory=list)


def _read_rows(file_path: Path) -> list[dict]:
    with file_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        if not REQUIRED_COLUMNS.issubset(columns):
            missing = REQUIRED_COLUMNS - columns
            raise ValueError(f"В файле не хватает колонок: {missing}")
        return list(reader)


def _validate_row(row: dict) -> dict:
    """Проверяет и приводит типы одной строки. Бросает ValueError/KeyError
    на некорректных данных. Этой же функцией пользуются и preview, и import,
    чтобы правила валидации не расходились между собой (DRY)."""
    vin = (row.get("vin") or "").strip().upper()
    if not vin:
        raise ValueError("пустой VIN")

    return {
        "vin": vin,
        "brand": (row.get("brand") or "").strip(),
        "model": (row.get("model") or "").strip(),
        "year": int(row["year"]),
        "mileage": int(row["mileage"]),
        "defects": (row.get("defects") or "").strip(),
        "dealer": (row.get("dealer") or "").strip(),
        "price": float(row["price"]),
    }


def upsert_car(db: Session, row: dict, source_name: str | None = None) -> bool:
    """Вставляет или обновляет одну машину по VIN. True — insert, False — update.
    Валидация идёт ДО db.add(), чтобы в сессию не попадали наполовину
    заполненные объекты при ошибке в строке."""
    data = _validate_row(row)

    car = db.query(Car).filter(Car.vin == data["vin"]).one_or_none()
    is_new = car is None
    if is_new:
        car = Car(vin=data["vin"])
        db.add(car)

    car.brand = data["brand"]
    car.model = data["model"]
    car.year = data["year"]
    car.mileage = data["mileage"]
    car.defects = data["defects"]
    car.dealer = data["dealer"]
    car.price = data["price"]
    if source_name:
        car.source_file = source_name

    return is_new


def import_file(db: Session, file_path: Path, source_name: str | None = None) -> ImportStats:
    rows = _read_rows(file_path)
    stats = ImportStats(total_rows=len(rows))
    name = source_name or file_path.name

    for row in rows:
        try:
            is_new = upsert_car(db, row, source_name=name)
        except (KeyError, ValueError):
            stats.skipped += 1
            continue

        if is_new:
            stats.inserted += 1
        else:
            stats.updated += 1

    db.commit()
    return stats


def preview_file(db: Session, file_path: Path) -> PreviewStats:
    """Считает, что произойдёт при импорте, НЕ трогая базу — только читает."""
    rows = _read_rows(file_path)
    stats = PreviewStats(total_rows=len(rows))
    seen_vins: set[str] = set()

    for i, row in enumerate(rows, start=2):  # +2: строка 1 в CSV — заголовок
        try:
            data = _validate_row(row)
        except (KeyError, ValueError) as error:
            stats.invalid_count += 1
            stats.warnings.append(f"Строка {i}: {error}")
            continue

        vin = data["vin"]
        if vin in seen_vins:
            stats.duplicate_in_file += 1
            stats.warnings.append(f"Строка {i}: VIN {vin} повторяется внутри файла")
        seen_vins.add(vin)

        exists = db.query(Car).filter(Car.vin == vin).one_or_none() is not None
        if exists:
            stats.update_count += 1
        else:
            stats.new_count += 1

    return stats