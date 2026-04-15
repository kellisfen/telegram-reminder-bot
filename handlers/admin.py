"""
Админские обработчики — работа с клиентами
"""
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from config import config
from handlers.states import BotStates


def is_admin(user_id: int) -> bool:
    """Проверка админских прав"""
    return user_id in config.admin_ids


async def list_clients(message: Message, state: FSMContext, **kwargs):
    """Список клиентов — /clients"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    sheets_client = kwargs.get("sheets_client")
    if not sheets_client:
        await message.answer("❌ Google Sheets не настроен.")
        return

    try:
        clients = sheets_client.get_all_clients()
        if not clients:
            await message.answer("📭 Клиентов пока нет.")
            return

        text = f"<b>📋 Клиенты ({len(clients)}):</b>\n\n"
        for i, client in enumerate(clients[:20], 1):  # Лимит 20
            name = client.get("username", "—")
            end_date = client.get("contract_end", "—")
            status = client.get("status", "—")
            text += f"{i}. {name}\n   📅 до {end_date} | ✅ {status}\n\n"

        if len(clients) > 20:
            text += f"\n...и ещё {len(clients) - 20} клиентов"

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


async def export_stats(message: Message, state: FSMContext, **kwargs):
    """Статистика — /stats"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    sheets_client = kwargs.get("sheets_client")
    if not sheets_client:
        await message.answer("❌ Google Sheets не настроен.")
        return

    try:
        clients = sheets_client.get_all_clients()
        total = len(clients)
        active = sum(1 for c in clients if c.get("status") == "активен")
        expiring = sum(1 for c in clients if c.get("status") == "скоро истекает")

        await message.answer(
            f"<b>📊 Статистика</b>\n\n"
            f"Всего клиентов: {total}\n"
            f"Активных: {active}\n"
            f"Скоро истекает: {expiring}",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


async def cmd_check_duplicates(message: Message, state: FSMContext, **kwargs):
    """Проверка дублей — /check_dups"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    sheets_client = kwargs.get("sheets_client")
    if not sheets_client:
        await message.answer("❌ Google Sheets не настроен.")
        return

    try:
        duplicates = sheets_client.find_duplicates()
        if not duplicates:
            await message.answer("✅ Дублей не найдено.")
            return

        text = f"<b>⚠️ Найдены дубли ({len(duplicates)}):</b>\n\n"
        for dup in duplicates:
            text += f"🔸 {dup['username']}\n   📝 {dup['comment']}\n\n"

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


async def link_client_start(message: Message, state: FSMContext, **kwargs):
    """Админ: привязать клиента к существующей записи — /link"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    await state.set_state(BotStates.waiting_link_username)
    await state.update_data(link_step="username")
    await message.answer(
        "🔗 <b>Привязка клиента к записи</b>\n\n"
        "Введи Telegram username клиента (например @ivanov):",
        parse_mode="HTML"
    )


async def link_enter_username(message: Message, state: FSMContext, **kwargs):
    """Админ ввёл username — показываем найденные записи"""
    username = message.text.strip()
    if not username.startswith("@"):
        username = "@" + username

    sheets_client = kwargs.get("sheets_client")
    if not sheets_client:
        await message.answer("❌ Google Sheets не настроен.")
        return

    clients = sheets_client.get_all_clients()
    # Ищем записи с таким username
    matches = [c for c in clients if c.get("username", "").lower() == username.lower()]

    if not matches:
        await message.answer(f"❌ Записи с username {username} не найдены.")
        await state.clear()
        return

    if len(matches) == 1:
        # Одна запись — сразу предлагаем привязать
        record = matches[0]
        await state.update_data(link_username=username, link_record_id=record.get("record_id"))
        await state.set_state(BotStates.waiting_link_select)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Привязать", callback_data="link_do"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="link_cancel"),
        ]])
        await message.answer(
            f"Найдена запись:\n"
            f"📋 {record.get('record_id', '—')} | {record.get('contact', '—')}\n"
            f"📅 {record.get('contract_start', '—')} — {record.get('contract_end', '—')}\n\n"
            f"Привязать?",
            reply_markup=kb
        )
    else:
        # Несколько записей — предлагаем выбрать
        await state.update_data(link_username=username, link_matches=matches)
        buttons = [
            [InlineKeyboardButton(
                text=f"{c.get('record_id', '?')} | {c.get('contact', '—')} | {c.get('contract_end', '—')}",
                callback_data=f"link_select_{c.get('record_id', '')}"
            )]
            for c in matches
        ]
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="link_cancel")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(f"Найдено {len(matches)} записей. Выбери:", reply_markup=kb)
        await state.set_state(BotStates.waiting_link_select)


async def link_select_record(message: Message, state: FSMContext, **kwargs):
    """Админ выбрал запись из списка — привязываем telegram_id"""
    # Это fallback если вдруг пришёл текст, но обычно выбор идёт через callback
    await message.answer("Выбери запись через кнопки.")


# ─── Callback handlers ───────────────────────────────────────────

async def link_do_callback(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Подтверждение привязки админом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    record_id = data.get("link_record_id")
    username = data.get("link_username", "")

    if not record_id:
        await callback.message.answer("❌ Запись не найдена.")
        await state.clear()
        return

    sheets_client = kwargs.get("sheets_client")
    client_state_db = kwargs.get("client_state_db")

    if not sheets_client:
        await callback.message.answer("❌ Sheets не настроен.")
        return

    # Обновляем запись в Sheets — оставляем username но теперь он "подтверждён"
    success = sheets_client.update_client_field(record_id, "status", "активен")
    if success:
        await callback.message.answer(
            f"✅ Запись {record_id} (username {username}) привязана.\n"
            f"Клиент будет получать напоминания!"
        )
    else:
        await callback.message.answer("❌ Ошибка при обновлении записи.")

    await state.clear()
    await callback.answer()


async def link_cancel_callback(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Отмена привязки"""
    await state.clear()
    await callback.message.answer("❌ Отменено.")
    await callback.answer()


async def link_select_callback(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Админ выбрал конкретную запись из списка"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    # callback.data = "link_select_<record_id>"
    record_id = callback.data.replace("link_select_", "")
    data = await state.get_data()
    username = data.get("link_username", "")

    sheets_client = kwargs.get("sheets_client")
    if not sheets_client:
        await callback.message.answer("❌ Sheets не настроен.")
        return

    # Обновляем статус
    success = sheets_client.update_client_field(record_id, "status", "активен")
    if success:
        await callback.message.answer(
            f"✅ Запись {record_id} привязана к {username}!"
        )
    else:
        await callback.message.answer("❌ Ошибка.")

    await state.clear()
    await callback.answer()

