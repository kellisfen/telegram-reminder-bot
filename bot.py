"""
Telegram-бот напоминалка для клиентов
Запускается: python bot.py
"""
import logging
import sys
import os

# Добавляем путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
import asyncio

from config import config, sheets_cfg
from handlers import admin, client, common
from sheets.client import SheetsClient
from db.state import ClientStateDB

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)


class BotStates(StatesGroup):
    """Состояния для админских команд"""
    waiting_for_contract_start = State()
    waiting_for_contract_months = State()
    waiting_for_contact = State()


def get_router() -> Router:
    """Создаёт и настраивает роутер с обработчиками"""
    router = Router()

    # Команды для всех
    router.message.register(common.cmd_start, CommandStart())
    router.message.register(common.cmd_help, Command("help"))
    router.message.register(common.cmd_cancel, Command("cancel"))

    # Клиентские обработчики (любой пользователь)
    router.message.register(client.add_client_flow_start, F.text == "📝 Добавить клиента")
    router.message.register(client.add_contract_start, BotStates.waiting_for_contract_start)
    router.message.register(client.add_contract_months, BotStates.waiting_for_contract_months)
    router.message.register(client.add_contact, BotStates.waiting_for_contact)

    # Админские обработчики (только по admin_ids)
    router.message.register(admin.list_clients, Command("clients"))
    router.message.register(admin.export_stats, Command("stats"))
    router.message.register(admin.cmd_check_duplicates, Command("check_dups"))

    return router


async def main():
    """Запуск бота"""
    log.info("🚀 Запуск Telegram-бота...")

    # Проверяем токен
    if not config.telegram_token:
        log.error("❌ TELEGRAM_BOT_TOKEN не установлен!")
        log.error("Создайте .env файл с TELEGRAM_BOT_TOKEN=your_token")
        sys.exit(1)

    # Инициализируем Google Sheets клиент
    try:
        sheets_client = SheetsClient(
            credentials_file=config.credentials_file,
            spreadsheet_id=config.spreadsheet_id
        )
        log.info("✅ Google Sheets клиент инициализирован")
    except Exception as e:
        log.warning(f"⚠️  Google Sheets не инициализирован: {e}")
        log.warning("   Бот запустится, но работа с таблицей будет недоступна")
        sheets_client = None

    # Инициализируем хранилище состояний клиентов
    client_state_db = ClientStateDB()

    # Создаём bot и dispatcher
    bot = Bot(token=config.telegram_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем роутер
    dp.include_router(get_router())

    # Передаём зависимости в bot_data
    dp["sheets_client"] = sheets_client
    dp["client_state_db"] = client_state_db

    log.info(f"✅ Бот авторизован. Admin IDs: {config.admin_ids}")
    log.info("📡 Ожидание сообщений...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 Бот остановлен")
