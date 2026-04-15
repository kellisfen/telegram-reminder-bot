"""
Клиентские обработчики — добавление клиента
"""
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime
import secrets

from config import config, sheets_cfg
from handlers.states import BotStates


async def client_link_yes(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Клиент подтвердил привязку к существующей записи"""
    user = callback.from_user
    data = await state.get_data()
    record_id = data.get("found_record_id")
    client_state_db = kwargs.get("client_state_db")
    sheets_client = kwargs.get("sheets_client")

    # Отмечаем в SQLite
    if client_state_db:
        client_state_db.mark_started(str(user.id))

    # Обновляем Telegram ID в Sheets
    if sheets_client and record_id:
        sheets_client.update_client_field(record_id, "telegram_id", str(user.id))
        sheets_client.update_client_field(record_id, "status", "активен")

    await callback.message.edit_text(
        f"✅ Готово! Ты привязан к записи {record_id}.\n"
        f"Теперь будешь получать напоминания!"
    )
    await callback.answer()


async def client_link_no(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Клиент отказался — предлагаем создать новую запись"""
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Добавить клиента")],
    ], resize_keyboard=True)
    await callback.message.edit_text(
        "Ок! Если захочешь добавить себя — нажми кнопку ниже.",
        reply_markup=kb
    )
    await callback.answer()


async def add_client_flow_start(message: Message, state: FSMContext, **kwargs):
    """Начало процесса добавления клиента (кнопка)"""
    user_id = message.from_user.id
    is_admin = user_id in config.admin_ids

    await state.set_state(BotStates.waiting_for_contract_start)
    await state.update_data(created_by="admin" if is_admin else "client")

    prompt = "📅 Введи дату начала договора (формат: ДД.ММ.ГГГГ):"
    await message.answer(prompt)


async def add_contract_start(message: Message, state: FSMContext, **kwargs):
    """Получена дата начала договора"""
    text = message.text.strip()

    try:
        date = datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        await message.answer("❌ Неверный формат. Введи дату в формате ДД.ММ.ГГГГ, например: 15.04.2025")
        return

    await state.update_data(contract_start=text, contract_start_date=date)
    await state.set_state(BotStates.waiting_for_contract_months)
    await message.answer("⏱️ Введи срок договора в месяцах (число):")


async def add_contract_months(message: Message, state: FSMContext, **kwargs):
    """Получен срок договора в месяцах"""
    text = message.text.strip()

    try:
        months = int(text)
        if months <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введи целое положительное число месяцев.")
        return

    await state.update_data(contract_months=months)
    await state.set_state(BotStates.waiting_for_contact)
    await message.answer("📱 Введи контакт клиента (Telegram username или телефон):")


async def add_contact(message: Message, state: FSMContext, **kwargs):
    """Получен контакт — завершаем добавление"""
    user = message.from_user
    data = await state.get_data()

    contact = message.text.strip()
    username = f"@{user.username}" if user.username else ""
    telegram_id = str(user.id)

    # Считаем даты
    from dateutil.relativedelta import relativedelta
    start_date: datetime = data["contract_start_date"]
    months = data["contract_months"]
    end_date = start_date + relativedelta(months=months)
    reminder_date = end_date - relativedelta(days=config.reminder_days_before)

    client_record = {
        "record_id": f"CL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2)}",
        "created_at": datetime.now().strftime("%d.%m.%Y"),
        "created_by": data["created_by"],
        "username": username,
        "telegram_id": telegram_id,
        "contact": contact,
        "contract_start": data["contract_start"],
        "contract_months": str(months),
        "contract_end": end_date.strftime("%d.%m.%Y"),
        "reminder_date": reminder_date.strftime("%d.%m.%Y"),
        "status": "активен",
        "is_duplicate": "",
        "dup_comment": "",
    }

    sheets_client = kwargs.get("sheets_client")
    client_state_db = kwargs.get("client_state_db")

    if sheets_client:
        try:
            sheets_client.add_client(client_record)
            if client_state_db and data["created_by"] == "client":
                client_state_db.mark_started(telegram_id)
        except Exception as e:
            await message.answer(f"⚠️ Запись создана, но не сохранена в Sheets: {e}")
            return
    else:
        await message.answer("⚠️ Sheets не настроен. Запись не сохранена.")
        return

    await state.clear()

    await message.answer(
        f"✅ <b>Клиент добавлен!</b>\n\n"
        f"📋 ID: {client_record['record_id']}\n"
        f"📅 Договор: {client_record['contract_start']} — {client_record['contract_end']}\n"
        f"⏰ Напоминание: {client_record['reminder_date']}",
        parse_mode="HTML"
    )
