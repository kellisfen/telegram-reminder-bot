# Scripts

## create_template.py

Создаёт шаблон Google Sheets с нужными колонками и форматированием.

**Перед запуском** — настрой Google Cloud:

1. [Google Cloud Console](https://console.cloud.google.com/) → создай проект
2. Включи API: **Google Sheets API** + **Google Drive API**
3. **IAM → Service Accounts → Create Service Account**
   - Назови `sheets-bot`
   - Роль: `Editor`
4. **Keys → Add Key → JSON** → скачай файл → сохрани как `credentials.json` в корне проекта
5. Вернись в проект и запусти:

```bash
python3 scripts/create_template.py -c credentials.json -s
```

**Что делает скрипт:**
- Создаёт таблицу в твоём Google Drive
- Записывает заголовки колонок (A-M)
- Форматирует первую строку (зелёный фон, белый bold текст)
- Автоматически открывает доступ сервисному аккаунту (если `-s`)

**После запуска:**
- Скопируй `SPREADSHEET_ID` из вывода скрипта → вставь в `.env`
- Или возьми ID из URL таблицы: `https://docs.google.com/spreadsheets/d/`**`ID`**`/edit`
