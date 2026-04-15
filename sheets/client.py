"""
Google Sheets API клиент
"""
import logging
from datetime import datetime
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import sheets_cfg

log = logging.getLogger(__name__)


class SheetsClient:
    """Клиент для работы с Google Sheets"""

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets"
    ]

    def __init__(self, credentials_file: str, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.service = self._get_service(credentials_file)

    def _get_service(self, credentials_file: str):
        """Авторизация через service account"""
        creds = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=self.SCOPES
        )
        return build("sheets", "v4", credentials=creds)

    def _row_to_dict(self, row: list) -> dict:
        """Конвертирует строку таблицы в dict по номерам колонок"""
        return {
            "record_id": row[sheets_cfg.col_record_id] if len(row) > sheets_cfg.col_record_id else "",
            "created_at": row[sheets_cfg.col_created_at] if len(row) > sheets_cfg.col_created_at else "",
            "created_by": row[sheets_cfg.col_created_by] if len(row) > sheets_cfg.col_created_by else "",
            "username": row[sheets_cfg.col_username] if len(row) > sheets_cfg.col_username else "",
            "telegram_id": row[sheets_cfg.col_telegram_id] if len(row) > sheets_cfg.col_telegram_id else "",
            "contact": row[sheets_cfg.col_contact] if len(row) > sheets_cfg.col_contact else "",
            "contract_start": row[sheets_cfg.col_contract_start] if len(row) > sheets_cfg.col_contract_start else "",
            "contract_months": row[sheets_cfg.col_contract_months] if len(row) > sheets_cfg.col_contract_months else "",
            "contract_end": row[sheets_cfg.col_contract_end] if len(row) > sheets_cfg.col_contract_end else "",
            "reminder_date": row[sheets_cfg.col_reminder_date] if len(row) > sheets_cfg.col_reminder_date else "",
            "status": row[sheets_cfg.col_status] if len(row) > sheets_cfg.col_status else "",
            "is_duplicate": row[sheets_cfg.col_is_duplicate] if len(row) > sheets_cfg.col_is_duplicate else "",
            "dup_comment": row[sheets_cfg.col_dup_comment] if len(row) > sheets_cfg.col_dup_comment else "",
        }

    def get_all_clients(self) -> list[dict]:
        """Получить все записи клиентов"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"Sheet1!A{sheets_cfg.header_row + 1}:M"  # Читаем от строки 2
            ).execute()

            rows = result.get("values", [])
            return [self._row_to_dict(row) for row in rows if row]

        except HttpError as e:
            log.error(f"Google Sheets API error: {e}")
            return []
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            return []

    def add_client(self, client: dict) -> bool:
        """Добавить нового клиента в таблицу"""
        row = [
            client.get("record_id", ""),
            client.get("created_at", ""),
            client.get("created_by", ""),
            client.get("username", ""),
            client.get("telegram_id", ""),
            client.get("contact", ""),
            client.get("contract_start", ""),
            client.get("contract_months", ""),
            client.get("contract_end", ""),
            client.get("reminder_date", ""),
            client.get("status", ""),
            client.get("is_duplicate", ""),
            client.get("dup_comment", ""),
        ]

        try:
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="Sheet1!A:A",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]}
            ).execute()
            log.info(f"Client added: {client['record_id']}")
            return True
        except HttpError as e:
            log.error(f"Failed to add client: {e}")
            return False

    def find_duplicates(self) -> list[dict]:
        """Найти дубликаты — все вхождения (и оригинал, и дубли) помечаются флагом"""
        clients = self.get_all_clients()
        duplicates = []
        seen = {}

        for client in clients:
            key = client.get("username", "").lower() or client.get("contact", "").lower()
            if not key:
                continue

            if key in seen:
                duplicates.append({
                    "username": client.get("username", ""),
                    "contact": client.get("contact", ""),
                    "record_id": client.get("record_id", ""),
                    "is_duplicate": True,
                    "original_record_id": seen[key]
                })
            else:
                seen[key] = client.get("record_id", "")

        # Отмечаем ВСЕ вхождения (оригинал + дубли) в таблице
        if duplicates:
            self._mark_duplicates(clients, duplicates, seen)

        return duplicates

    def _mark_duplicates(self, clients: list, duplicates: list, seen: dict):
        """Ставит флаг во всех вхождениях — и оригинал, и дубли"""
        # Собираем все record_id которые участвуют в дублях
        all_dup_record_ids = set()
        for d in duplicates:
            all_dup_record_ids.add(d["record_id"])
            if d.get("original_record_id"):
                all_dup_record_ids.add(d["original_record_id"])

        rows_to_update = []
        for i, client in enumerate(clients, self._sheet_start_row()):
            if client.get("record_id", "") in all_dup_record_ids:
                rows_to_update.append(i)

        if not rows_to_update:
            return

        data = []
        for row_num in rows_to_update:
            data.append({
                "range": f"Sheet1!L{row_num}:M{row_num}",
                "values": [["да", "Требует проверки"]]
            })

        try:
            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"valueRanges": data, "valueInputOption": "RAW"}
            ).execute()
            log.info(f"Marked {len(rows_to_update)} duplicate rows")
        except HttpError as e:
            log.error(f"Failed to mark duplicates: {e}")

    def update_client_field(self, record_id: str, field: str, value: str) -> bool:
        """Обновляет одно поле записи по record_id"""
        try:
            clients = self.get_all_clients()
            for i, client in enumerate(clients, self._sheet_start_row()):
                if client.get("record_id") == record_id:
                    col_letter = self._col_index_to_letter(getattr(sheets_cfg, f"col_{field}" if hasattr(sheets_cfg, f"col_{field}") else f"col_{field}"))
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f"Sheet1!{col_letter}{i}",
                        valueInputOption="RAW",
                        body={"values": [[value]]}
                    ).execute()
                    return True
            return False
        except Exception as e:
            log.error(f"Failed to update field: {e}")
            return False

    def _sheet_start_row(self) -> int:
        """Номер первой строки с данными"""
        return sheets_cfg.header_row + 1

    def _col_index_to_letter(self, col_index: int) -> str:
        """Конвертирует номер колонки (0-based) в букву (A=0 → A, B=1 → B)"""
        return chr(ord("A") + col_index)
