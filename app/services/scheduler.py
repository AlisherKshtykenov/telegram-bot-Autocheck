"""
Cron-триггер загрузки. Раз в settings.cron_schedule сканирует
data/uploads/incoming/ на новые CSV, импортирует каждый через тот же
import_file(), что и webhook/Telegram, и переносит обработанные файлы
в data/uploads/processed/ (чтобы не читать повторно).
"""

from __future__ import annotations

import shutil

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import SessionLocal
from app.services.parser import import_file

INCOMING_DIR = settings.uploads_dir / "incoming"
PROCESSED_DIR = settings.uploads_dir / "processed"


def scan_and_import() -> None:
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(INCOMING_DIR.glob("*.csv"))
    if not csv_files:
        print("[cron] новых файлов нет")
        return

    db = SessionLocal()
    try:
        for file_path in csv_files:
            stats = import_file(db, file_path, source_name=f"cron:{file_path.name}")
            print(f"[cron] {file_path.name}: {stats}")
            shutil.move(str(file_path), str(PROCESSED_DIR / file_path.name))
    finally:
        db.close()


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        scan_and_import,
        trigger=CronTrigger.from_crontab(settings.cron_schedule),
        id="scan_incoming_uploads",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler