"""
Админские обработчики — работа с клиентами
"""
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import config


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
