import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    db_url: str
    uploads_dir: Path
    cron_schedule: str
    bot_token: str
    webapp_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_url=os.getenv("DB_URL", f"sqlite:///{BASE_DIR / 'data' / 'autocheck.db'}"),
            uploads_dir=BASE_DIR / "data" / "uploads",
            cron_schedule=os.getenv("CRON_SCHEDULE", "*/30 * * * *"),
            bot_token=os.getenv("BOT_TOKEN", ""),
            webapp_url=os.getenv("WEBAPP_URL", ""),
        )


settings = Settings.from_env()