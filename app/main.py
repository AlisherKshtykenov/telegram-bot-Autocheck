"""
Точка входа FastAPI-приложения.
Запуск: uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import cars, upload
from app.services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)   # для MVP; в проде — Alembic
    scheduler = start_scheduler()      # cron-триггер живёт вместе с сервером
    yield
    scheduler.shutdown()


app = FastAPI(title="Autocheck MVP", lifespan=lifespan)

app.include_router(upload.router)
app.include_router(cars.router)

# порядок важен: /upload и /cars регистрируются раньше, поэтому static
# перехватывает только всё остальное (в т.ч. "/")
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")