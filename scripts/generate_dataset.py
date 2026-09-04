"""
Скрипт/модуль генерации фейковой выгрузки автомобилей из 1С.

Как CLI:
    python scripts/generate_dataset.py --rows 200 --out data/uploads/export.csv
Как модуль (для seed_demo.py):
    from scripts.generate_dataset import write_dataset
"""

from __future__ import annotations

import argparse
import csv
import random
import string
from pathlib import Path

from faker import Faker

fake = Faker("ru_RU")

CAR_CATALOG = {
    "Toyota": ["Camry", "Corolla", "RAV4", "Land Cruiser"],
    "Hyundai": ["Elantra", "Tucson", "Santa Fe", "Sonata"],
    "Kia": ["Rio", "Sportage", "Sorento", "Cerato"],
    "Lada": ["Vesta", "Granta", "Niva", "XRAY"],
    "BMW": ["3 Series", "5 Series", "X3", "X5"],
    "Mercedes-Benz": ["C-Class", "E-Class", "GLC", "GLE"],
}

DEFECTS_POOL = [
    "скол на лобовом стекле",
    "царапина на бампере",
    "износ протектора шин",
    "не работает кондиционер",
    "коррозия порогов",
    "неисправность датчика давления в шинах",
    "трещина на фаре",
    "потёртости салона",
]

VIN_ALLOWED_CHARS = [c for c in string.ascii_uppercase + string.digits if c not in "IOQ"]


def generate_vin() -> str:
    return "".join(random.choices(VIN_ALLOWED_CHARS, k=17))


def generate_row() -> dict:
    brand = random.choice(list(CAR_CATALOG.keys()))
    model = random.choice(CAR_CATALOG[brand])
    defects_count = random.choices([0, 1, 2, 3], weights=[40, 30, 20, 10])[0]
    defects = ", ".join(random.sample(DEFECTS_POOL, k=defects_count)) if defects_count else "нет дефектов"

    return {
        "vin": generate_vin(),
        "brand": brand,
        "model": model,
        "year": random.randint(2015, 2025),
        "mileage": random.randint(0, 200_000),
        "defects": defects,
        "dealer": fake.company(),
        "price": round(random.uniform(4_000_000, 25_000_000), -3),
    }


def write_dataset(rows: int, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["vin", "brand", "model", "year", "mileage", "defects", "dealer", "price"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for _ in range(rows):
            writer.writerow(generate_row())


def main() -> None:
    parser = argparse.ArgumentParser(description="Генератор фейковой выгрузки автомобилей из 1С")
    parser.add_argument("--rows", type=int, default=100)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    out_path = Path(args.out) if args.out else Path("data/uploads/export_demo.csv")
    write_dataset(args.rows, out_path)
    print(f"Сгенерировано {args.rows} строк -> {out_path}")


if __name__ == "__main__":
    main()
