"""
Telegram-бот: клиент присылает CSV-файл выгрузки. Бот считает статистику
через preview_file() (БЕЗ записи в базу), показывает её и просит
подтверждение. Только после «Да» данные реально попадают в базу через
import_file(); при «Нет» — файл удаляется, сообщение с превью удаляется.

Запуск отдельным процессом (параллельно с веб-сервером):
    python -m app.telegram_bot
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app.config import settings
from app.database import SessionLocal
from app.services.parser import import_file, preview_file

router = Router(name="dataset_upload")

ALLOWED_EXTENSIONS = {".csv"}
MAX_WARNINGS_SHOWN = 5


class DatasetUploadForm(StatesGroup):
    waiting_for_confirmation = State()


class ConfirmImportCallback(CallbackData, prefix="confirm_import"):
    agree: bool


def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Добавить в базу", callback_data=ConfirmImportCallback(agree=True))
    builder.button(text="❌ Отмена", callback_data=ConfirmImportCallback(agree=False))
    builder.adjust(1)
    return builder.as_markup()


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚗 Открыть список авто", web_app=WebAppInfo(url=settings.webapp_url))
    return builder.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Пришлите CSV-файл выгрузки — покажу превью и загружу по подтверждению.\n"
        "Либо откройте список машин прямо в приложении:",
        reply_markup=main_menu_keyboard(),
    )

 

@router.message(F.document)
async def handle_dataset(message: Message, bot: Bot, state: FSMContext) -> None:
    document = message.document
    file_ext = Path(document.file_name or "").suffix.lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        await message.reply("⚠️ Поддерживаются только CSV-файлы (.csv).")
        return

    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"telegram_{message.from_user.id}_{document.file_unique_id}.csv"
    dest_path = settings.uploads_dir / safe_name
    await bot.download(document, destination=dest_path)

    db = SessionLocal()
    try:
        preview = preview_file(db, dest_path)
    except ValueError as error:
        dest_path.unlink(missing_ok=True)
        await message.reply(f"⚠️ Ошибка в файле: {error}")
        return
    finally:
        db.close()

    text = (
        "📊 Предпросмотр файла (в базу пока НЕ записано):\n\n"
        f"Всего строк: {preview.total_rows}\n"
        f"Новых машин: {preview.new_count}\n"
        f"Будет обновлено (совпадение по VIN): {preview.update_count}\n"
        f"Некорректных строк (будут пропущены): {preview.invalid_count}\n"
        f"Повторов VIN внутри файла: {preview.duplicate_in_file}\n"
    )

    if preview.warnings:
        shown = preview.warnings[:MAX_WARNINGS_SHOWN]
        text += "\n⚠️ Предупреждения:\n" + "\n".join(shown)
        if len(preview.warnings) > MAX_WARNINGS_SHOWN:
            text += f"\n… и ещё {len(preview.warnings) - MAX_WARNINGS_SHOWN}"

    text += "\n\nДобавить эти данные в базу?"

    await state.set_state(DatasetUploadForm.waiting_for_confirmation)
    await state.update_data(file_path=str(dest_path))

    await message.reply(text, reply_markup=confirm_keyboard())


@router.callback_query(DatasetUploadForm.waiting_for_confirmation, ConfirmImportCallback.filter())
async def on_confirm_import(
    query: CallbackQuery,
    callback_data: ConfirmImportCallback,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    file_path = Path(data["file_path"])
    await state.clear()

    if not callback_data.agree:
        file_path.unlink(missing_ok=True)
        await query.message.delete()
        await query.answer("Отменено, файл удалён")
        return

    db = SessionLocal()
    try:
        stats = import_file(db, file_path, source_name=f"telegram:{query.from_user.id}")
    finally:
        db.close()

    await query.message.edit_text(
        "✅ Загружено в базу!\n\n"
        f"Всего строк: {stats.total_rows}\n"
        f"Новых машин: {stats.inserted}\n"
        f"Обновлено: {stats.updated}\n"
        f"Пропущено (ошибки в данных): {stats.skipped}"
    )
    await query.answer()


async def main() -> None:
    bot = Bot(token=settings.bot_token)
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="Машины", web_app=WebAppInfo(url=settings.webapp_url))
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())