#!/usr/bin/env python3
"""
Скрипт для создания шаблона Google Sheets.
Запускать после настройки Google Cloud и получения credentials.json

Usage:
    python3 scripts/create_template.py
"""
import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Заголовки колонок (对应的 поля из config.py)
HEADERS = [
    "ID записи",           # A
    "Дата создания",       # B
    "Кто создал",          # C (admin/client)
    "Telegram username",   # D
    "Telegram ID",         # E
    "Контакт",             # F
    "Дата начала",         # G
    "Срок (мес)",          # H
    "Дата окончания",      # I
    "Дата напоминания",    # J
    "Статус",              # K
    "Дубль",               # L
    "Комментарий",         # M
]


def get_credentials(credentials_file: str):
    """Авторизация через service account"""
    creds = service_account.Credentials.from_service_account_file(
        credentials_file, scopes=SCOPES
    )
    return creds


def create_spreadsheet(service, title: str = "Бот-напоминалка: База клиентов"):
    """Создаёт новую таблицу и возвращает её ID"""

    # 1. Создаём spreadsheet
    spreadsheet = service.spreadsheets().create(
        body={
            "properties": {"title": title},
            "sheets": [
                {
                    "properties": {
                        "title": "Клиенты",
                        "gridProperties": {"frozenRowCount": 1},
                    }
                }
            ],
        }
    ).execute()

    spreadsheet_id = spreadsheet["spreadsheetId"]
    spreadsheet_url = spreadsheet.get("spreadsheetUrl", f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

    print(f"✅ Таблица создана!")
    print(f"   ID: {spreadsheet_id}")
    print(f"   URL: {spreadsheet_url}")
    print()

    # 2. Записываем заголовки
    sheet_id = spreadsheet["sheets"][0]["properties"]["sheetId"]

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Клиенты!A1:M1",
        valueInputOption="RAW",
        body={"values": [HEADERS]}
    ).execute()

    # 3. Форматируем заголовки
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.4},
                                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                                "horizontalAlignment": "CENTER",
                            }
                        },
                        "fields": "userEnteredFormat",
                    }
                },
                {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": 13,
                        }
                    }
                },
                # Пример строки с данными (пустая, но показывает формат)
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2},
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95},
                            }
                        },
                        "fields": "userEnteredFormat",
                    }
                },
            ]
        }
    ).execute()

    print("✅ Заголовки записаны и отформатированы")
    print(f"   Лист: 'Клиенты', диапазон A1:M1")
    print()
    print("📋 Следующие шаги:")
    print(f"   1. Открой таблицу: {spreadsheet_url}")
    print(f"   2. Нажми 'Поделиться' → добавь email сервисного аккаунта (смотри в credentials.json)")
    print(f"   3. Скопируй ID таблицы из URL и добавь в .env → SPREADSHEET_ID")
    print()
    print(f"   Формат ID в URL: https://docs.google.com/spreadsheets/d/[ВОТ_ЭТОТ_ID]/edit")
    print()

    return spreadsheet_id


def share_with_service_account(service, spreadsheet_id: str, credentials_file: str):
    """Даёт сервисному аккаунту доступ к таблице"""
    import json
    with open(credentials_file) as f:
        creds_data = json.load(f)
    service_email = creds_data.get("client_email")

    if not service_email:
        print("⚠️  Не удалось найти email сервисного аккаунта в credentials.json")
        return

    try:
        service.permissions().create(
            fileId=spreadsheet_id,
            body={
                "type": "user",
                "role": "writer",
                "emailAddress": service_email,
            },
        ).execute()
        print(f"✅ Таблица открыта для {service_email}")
    except HttpError as e:
        if " sharingLimit" in str(e):
            print(f"⚠️  Лимит шаринга. Открой таблицу вручную и добавь {service_email} как редактора")
        else:
            print(f"⚠️  Ошибка шаринга: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Создаёт шаблон Google Sheets для бота")
    parser.add_argument(
        "--credentials", "-c",
        default="credentials.json",
        help="Путь к credentials.json (по умолчанию: credentials.json)"
    )
    parser.add_argument(
        "--title", "-t",
        default="Бот-напоминалка: База клиентов",
        help="Название таблицы"
    )
    parser.add_argument(
        "--share", "-s",
        action="store_true",
        help="Автоматически открыть доступ сервисному аккаунту"
    )
    args = parser.parse_args()

    credentials_file = args.credentials

    if not os.path.exists(credentials_file):
        print(f"❌ Файл {credentials_file} не найден!")
        print()
        print("📌 Для настройки Google Cloud:")
        print("   1. Перейди в https://console.cloud.google.com/")
        print("   2. Создай проект (или выбери существующий)")
        print("   3. Включи Google Sheets API и Google Drive API")
        print("   4. Создай Service Account:")
        print("      IAM → Service Accounts → Create → Service Account")
        print("   5. Создай ключ: Keys → Add Key → JSON")
        print(f"   6. Скачай файл и сохрани как '{credentials_file}' в папке проекта")
        print()
        print("   После скачивания вернись и запусти:")
        print(f"   python3 scripts/create_template.py -c {credentials_file} -s")
        sys.exit(1)

    print(f"🔐 Авторизация через {credentials_file}...")
    creds = get_credentials(credentials_file)
    service = build("sheets", "v4", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    # Подменяем sheets на drive scope для шаринга
    spreadsheet_id = create_spreadsheet(service, title=args.title)

    if args.share:
        share_with_service_account(service, spreadsheet_id, credentials_file)

    print("✅ Шаблон готов!")


if __name__ == "__main__":
    main()
