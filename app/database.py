from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# check_same_thread=False нужен только для SQLite: по умолчанию SQLite запрещает
# использовать соединение из другого потока, а FastAPI/APScheduler могут это делать.
connect_args = {"check_same_thread": False} if settings.db_url.startswith("sqlite") else {}

engine = create_engine(settings.db_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: одна сессия SQLAlchemy на один HTTP-запрос."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()