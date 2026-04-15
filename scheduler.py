"""
Шедулер напоминаний — проверяет даты и отправляет уведомления
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import config, sheets_cfg
from sheets.client import SheetsClient
from db.state import ClientStateDB

log = logging.getLogger(__name__)


class ReminderScheduler:
    """Шедулер для напоминаний о договорах"""

    def __init__(self, bot, sheets_client: SheetsClient, client_state_db: ClientStateDB):
        self.bot = bot
        self.sheets_client = sheets_client
        self.client_state_db = client_state_db
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Запускает шедулер"""
        self.scheduler.add_job(
            self.check_reminders,
            trigger=IntervalTrigger(hours=config.check_interval_hours),
            id="reminder_check",
            replace_existing=True
        )
        self.scheduler.start()
        log.info(f"✅ Шедулер запущен (проверка каждые {config.check_interval_hours} ч.)")

    def stop(self):
        """Останавливает шедулер"""
        self.scheduler.shutdown()
        log.info("⏹ Шедулер остановлен")

    async def check_reminders(self):
        """Проверяет всех клиентов и отправляет напоминания"""
        log.info("🔍 Проверка напоминаний...")

        if not self.sheets_client:
            log.warning("Sheets не инициализирован, пропускаем")
            return

        clients = self.sheets_client.get_all_clients()
        today = datetime.now().date()
        notified = 0

        for client in clients:
            reminder_date_str = client.get("reminder_date", "")
            if not reminder_date_str:
                continue

            try:
                reminder_date = datetime.strptime(reminder_date_str, "%d.%m.%Y").date()
            except ValueError:
                continue

            # Напоминаем если дата напоминания <= сегодня и статус не "напомнено"
            if reminder_date <= today and client.get("status") != "напомнено":
                await self._send_reminder(client)
                notified += 1

        log.info(f"✅ Отправлено напоминаний: {notified}")

    async def _send_reminder(self, client: dict):
        """Отправляет напоминание клиенту и/или админу"""
        telegram_id = client.get("telegram_id", "")
        admin_ids = config.admin_ids
        has_started = self.client_state_db.has_started(telegram_id)
        created_by = client.get("created_by", "")

        contract_end = client.get("contract_end", "")
        client_username = client.get("username", "—")

        # Формируем текст напоминания
        reminder_text = (
            f"⏰ <b>Напоминание!</b>\n\n"
            f"Договор клиента {client_username} истекает <b>{contract_end}</b>.\n"
            f"Для проверки нажми /clients"
        )

        # Логика: если клиент сам запускал бота — шлём и клиенту, и админу
        # Если админ создал запись — только админу
        sent_to = []

        if has_started or created_by == "client":
            # Шлём клиенту
            if telegram_id:
                try:
                    await self.bot.send_message(
                        chat_id=int(telegram_id),
                        text=f"🔔 {client_username}, твой договор истекает <b>{contract_end}</b>!\nОбратись к администратору для продления.",
                        parse_mode="HTML"
                    )
                    sent_to.append(f"клиенту {client_username}")
                except Exception as e:
                    log.warning(f"Не удалось отправить клиенту {telegram_id}: {e}")

        # Всегда шлём админам
        for admin_id in admin_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=reminder_text,
                    parse_mode="HTML"
                )
                sent_to.append(f"админу")
            except Exception as e:
                log.warning(f"Не удалось отправить админу {admin_id}: {e}")

        # Обновляем статус в Sheets
        if sent_to:
            self._mark_reminded(client)

        log.info(f"📤 Напоминание отправлено: {', '.join(sent_to)}")

    def _mark_reminded(self, client: dict):
        """Отмечает что напоминание отправлено"""
        # Находим строку клиента и обновляем статус
        try:
            # Простой поиск по record_id
            clients = self.sheets_client.get_all_clients()
            for i, c in enumerate(clients, sheets_cfg.header_row + 1):
                if c.get("record_id") == client.get("record_id"):
                    # Обновляем статус на "напомнено"
                    self.sheets_client.service.spreadsheets().values().update(
                        spreadsheetId=self.sheets_client.spreadsheet_id,
                        range=f"Sheet1!K{i}",
                        valueInputOption="RAW",
                        body={"values": [["напоминание отправлено"]]}
                    ).execute()
                    break
        except Exception as e:
            log.error(f"Не удалось обновить статус: {e}")
