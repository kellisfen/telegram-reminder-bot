"""
Конфигурация бота — все секреты и настройки
"""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    """Основные настройки бота"""
    telegram_token: str = field(default="")
    admin_ids: list[int] = field(default_factory=list)
    spreadsheet_id: str = field(default="")
    credentials_file: str = field(default="credentials.json")
    reminder_days_before: int = 60
    check_interval_hours: int = 1

    def __post_init__(self):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.admin_ids = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID", "")
        self.credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        self.reminder_days_before = int(os.getenv("REMINDER_DAYS_BEFORE", "60"))
        self.check_interval_hours = int(os.getenv("CHECK_INTERVAL_HOURS", "1"))


@dataclass
class SheetsConfig:
    """Настройки таблицы — имена колонок"""
    # Номер строки с заголовками (обычно 1)
    header_row: int = 1
    # Колонки (A=0, B=1, ...)
    col_record_id: int = 0       # A - ID записи
    col_created_at: int = 1      # B - Дата создания
    col_created_by: int = 2      # C - Кто создал (admin/client)
    col_username: int = 3         # D - Telegram username
    col_telegram_id: int = 4     # E - Telegram ID
    col_contact: int = 5         # F - Контакт для ручного поиска
    col_contract_start: int = 6  # G - Дата начала договора
    col_contract_months: int = 7 # H - Срок договора (месяцев)
    col_contract_end: int = 8    # I - Дата окончания
    col_reminder_date: int = 9   # J - Дата напоминания
    col_status: int = 10         # K - Статус записи
    col_is_duplicate: int = 11  # L - Признак дубля
    col_dup_comment: int = 12    # M - Комментарий по дублю


config = BotConfig()
sheets_cfg = SheetsConfig()
