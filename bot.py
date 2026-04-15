"""
Telegram-бот напоминалка для клиентов
Запускается: python bot.py
"""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

from config import config
from handlers import admin, client, common
from handlers.states import BotStates
from sheets.client import SheetsClient
from db.state import ClientStateDB
from scheduler import ReminderScheduler

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)


def get_router() -> Router:
    """Создаёт роутер с обработчиками"""
    router = Router()

    # Команды для всех
    router.message.register(common.cmd_help, Command("help"))
    router.message.register(common.cmd_cancel, Command("cancel"))

    # /start — единый обработчик с логикой клиента
    router.message.register(common.cmd_start, CommandStart())

    # Клиентское добавление (FSM)
    router.message.register(client.add_client_flow_start, F.text == "📝 Добавить клиента")
    router.message.register(client.add_contract_start, BotStates.waiting_for_contract_start)
    router.message.register(client.add_contract_months, BotStates.waiting_for_contract_months)
    router.message.register(client.add_contact, BotStates.waiting_for_contact)

    # Админские команды
    router.message.register(admin.list_clients, Command("clients"))
    router.message.register(admin.export_stats, Command("stats"))
    router.message.register(admin.cmd_check_duplicates, Command("check_dups"))

    # Админ: привязка клиента к существующей записи
    router.message.register(admin.link_client_start, Command("link"))
    router.message.register(admin.link_enter_username, BotStates.waiting_link_username)
    router.message.register(admin.link_select_record, BotStates.waiting_link_select)

    # Callbacks — админ
    router.callback_query.register(admin.link_do_callback, F.data == "link_do")
    router.callback_query.register(admin.link_cancel_callback, F.data == "link_cancel")
    router.callback_query.register(admin.link_select_callback, F.data.startswith("link_select_"))

    # Callbacks — клиент
    router.callback_query.register(client.client_link_yes, F.data == "client_link_yes")
    router.callback_query.register(client.client_link_no, F.data == "client_link_no")

    return router


async def main():
    """Запуск бота"""
    log.info("🚀 Запуск Telegram-бота...")

    if not config.telegram_token:
        log.error("❌ TELEGRAM_BOT_TOKEN не установлен!")
        log.error("Создайте .env файл с TELEGRAM_BOT_TOKEN=your_token")
        sys.exit(1)

    # Google Sheets клиент
    try:
        sheets_client = SheetsClient(
            credentials_file=config.credentials_file,
            spreadsheet_id=config.spreadsheet_id
        )
        log.info("✅ Google Sheets клиент инициален")
    except Exception as e:
        log.warning(f"⚠️  Google Sheets не инициализирован: {e}")
        log.warning("   Бот запустится, но работа с таблицей недоступна")
        sheets_client = None

    # SQLite — кто запускал бота
    client_state_db = ClientStateDB()

    # Telegram bot
    bot = Bot(token=config.telegram_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(get_router())

    dp["sheets_client"] = sheets_client
    dp["client_state_db"] = client_state_db

    # Запускаем scheduler
    reminder_scheduler = None
    if sheets_client:
        reminder_scheduler = ReminderScheduler(bot, sheets_client, client_state_db)
        reminder_scheduler.start()
        log.info("✅ ReminderScheduler запущен")
    else:
        log.warning("⚠️  Scheduler не запущен (нет Sheets)")

    log.info(f"✅ Бот авторизован. Admin IDs: {config.admin_ids}")
    log.info("📡 Ожидание сообщений...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if reminder_scheduler:
            reminder_scheduler.stop()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 Бот остановлен")
