"""
Общие обработчики — /start, /help, /cancel
"""
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import config


async def cmd_start(message: Message, state: FSMContext):
    """Обработка /start"""
    user = message.from_user
    is_admin = user.id in config.admin_ids

    await state.clear()

    admin_text = (
        "👋 <b>Привет, администратор!</b>\n\n"
        "Ты в боте напоминалке.\n"
        "Доступные команды:\n"
        "• /help — помощь\n"
        "• /clients — список клиентов\n"
        "• /stats — статистика\n"
        "• /check_dups — проверить дубликаты\n\n"
        "📝 <b>Добавить клиента:</b> кнопка в меню"
    ) if is_admin else (
        "👋 <b>Привет!</b>\n\n"
        "Я бот для напоминаний о сроках договоров.\n"
        "Используй /help для помощи."
    )

    await message.answer(admin_text, parse_mode="HTML")


async def cmd_help(message: Message, state: FSMContext):
    """Обработка /help"""
    await state.clear()
    await message.answer(
        "<b>📖 Помощь</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — начать\n"
        "/help — эта помощь\n"
        "/cancel — отменить текущее действие\n\n"
        "<b>Как это работает:</b>\n"
        "Бот хранит данные о договорах и присылает "
        "напоминания за 2 месяца до окончания срока.",
        parse_mode="HTML"
    )


async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("ℹ️ Нечего отменять.")
        return

    await state.clear()
    await message.answer("✅ Действие отменено.")
