"""
Общие обработчики — /start, /help, /cancel
"""
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from config import config


async def cmd_start(message: Message, state: FSMContext, **kwargs):
    """
    /start — единый обработчик для всех пользователей.
    Клиент: пытаемся найти существующую запись и привязать Telegram ID.
    Админ: приветственное меню с админскими командами.
    """
    user = message.from_user
    is_admin = user.id in config.admin_ids
    client_state_db = kwargs.get("client_state_db")
    sheets_client = kwargs.get("sheets_client")

    await state.clear()

    # Отмечаем что клиент запускал бота (для логики напоминаний)
    if client_state_db:
        client_state_db.mark_started(str(user.id))

    username = f"@{user.username}" if user.username else ""

    if is_admin:
        # Админское меню
        kb = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📝 Добавить клиента")],
        ], resize_keyboard=True)
        await message.answer(
            "👋 <b>Привет, администратор!</b>\n\n"
            "Ты в боте напоминалке.\n"
            "Доступные команды:\n"
            "• /help — помощь\n"
            "• /clients — список клиентов\n"
            "• /stats — статистика\n"
            "• /check_dups — проверить дубликаты\n"
            "• /link — привязать клиента к записи",
            parse_mode="HTML",
            reply_markup=kb
        )
        return

    # Клиент — пробуем найти существующую запись по username
    found_record = None
    if sheets_client and username:
        clients = sheets_client.get_all_clients()
        for c in clients:
            if c.get("username", "").lower().strip("@") == username.lower().strip("@"):
                found_record = c
                break

    if found_record:
        # Нашли запись — предлагаем привязаться
        await state.update_data(found_record_id=found_record.get("record_id"))
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Да, это я", callback_data="client_link_yes"),
            InlineKeyboardButton(text="❌ Нет, создать новую", callback_data="client_link_no"),
        ]])
        await message.answer(
            f"👋 Привет, {username}!\n\n"
            f"Мы нашли твою запись в базе:\n"
            f"📋 ID: {found_record.get('record_id', '—')}\n"
            f"📅 Договор: {found_record.get('contract_start', '—')} — {found_record.get('contract_end', '—')}\n\n"
            f"Хочешь привязать свой Telegram ID к этой записи?",
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        # Новый клиент
        kb = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📝 Добавить клиента")],
        ], resize_keyboard=True)
        await message.answer(
            f"👋 Привет, {username}!\n\n"
            f"Ты зарегистрирован в системе.\n"
            f"Когда подойдёт срок окончания твоего договора — мы напомним! 📅",
            parse_mode="HTML",
            reply_markup=kb
        )


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
