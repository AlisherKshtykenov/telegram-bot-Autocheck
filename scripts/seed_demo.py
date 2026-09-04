"""
Наполняет базу демо-данными при первом запуске контейнера — чтобы
проверяющий сразу увидел рабочий список машин, а не пустую таблицу.
Безопасно запускать многократно: если данные уже есть — ничего не делает.
"""

from __future__ import annotations

from pathlib import Path

from app.database import Base, SessionLocal, engine
from app.models import Car
from app.services.parser import import_file
from scripts.generate_dataset import write_dataset

DEMO_FILE = Path("data/uploads/demo_seed.csv")


def seed() -> None:
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        if db.query(Car).first() is not None:
            print("[seed] в базе уже есть данные, пропускаю")
            return
    finally:
        db.close()

    write_dataset(60, DEMO_FILE)

    db = SessionLocal()
    try:
        stats = import_file(db, DEMO_FILE, source_name="seed:demo")
        print(f"[seed] загружено демо-данных: {stats}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
