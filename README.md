# Telegram-бот напоминалка для клиентов

Автоматический бот, который хранит данные о договорах клиентов в Google Sheets и присылает напоминания перед окончанием срока.

## Возможности

- Данные клиентов хранятся в Google Sheets (база не привязана к боту)
- Добавление клиентов через бота — админом или самим клиентом
- Автоматический расчёт: дата окончания = дата начала + срок (мес)
- Напоминание = дата окончания − 2 месяца (настраивается)
- Проверка на дубликаты (похожие username/контакт → флаг в Sheets)
- **Автоматическая привязка**: клиент нажал `/start` → бот нашёл его запись по username → предложил привязаться кнопкой
- **Команда /link**: админ может привязать клиента к существующей записи вручную
- Scheduler работает 24/7 (APScheduler), проверяет даты каждый час

---

## Стек

| Компонент | Технология |
|-----------|------------|
| Бот | Python 3.11 + aiogram 3 |
| База данных | Google Sheets API |
| Локальное хранилище | SQLite (кто запускал бота) |
| Планировщик | APScheduler |
| Авторизация | Service Account (Google) |

---

## Быстрый старт

### 1. Клонирование

```bash
git clone https://github.com/kellisfen/telegram-reminder-bot.git
cd telegram-reminder-bot
```

### 2. Виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows
```

### 3. Зависимости

```bash
pip install -r requirements.txt
```

### 4. Telegram токен

1. Открой Telegram, найди **[@BotFather](https://t.me/BotFather)**
2. Отправь `/newbot`
3. Следуй инструкциям → задай имя и username боту
4. Скопируй токен (выглядит как `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 5. Google Cloud (Service Account)

> Это самый важный и длинный шаг. Выполни внимательно.

**Шаг 5.1 — создать проект**

1. Перейди на [Google Cloud Console](https://console.cloud.google.com/)
2. Нажми **"Select a project"** → **"New Project"**
3. Название: `telegram-reminder-bot` (любое)
4. Нажми **"Create"**

**Шаг 5.2 — включить API**

1. В меню слева: **"APIs & Services"** → **"Library"**
2. Найди и включи:
   - **Google Sheets API**
   - **Google Drive API**

**Шаг 5.3 — создать Service Account**

1. Меню слева: **"IAM & Admin"** → **"Service Accounts"**
2. Нажми **"+ Create Service Account"**
3. Имя: `sheets-bot` → **"Create and continue"**
4. Роль: **"Editor"** → **"Done"**

**Шаг 5.4 — создать ключ**

1. Нажми на созданный Service Account
2. Вкладка **"Keys"** → **"Add Key"** → **"JSON"**
3. Скачается файл (например `telegram-reminder-bot-123456-abc.json`)
4. Переименуй в `credentials.json` и положи в корень проекта

**Шаг 5.5 — открыть доступ к таблицам (для шаринга)**

> Примечание: если ты единственный пользователь таблицы — этот шаг можно пропустить.

Вернись в **Service Accounts** → найди свой аккаунт → скопируй **Email** (например `sheets-bot@project.iam.gserviceaccount.com`).

Этот email понадобится для шаринга таблицы.

### 6. Создание таблицы

```bash
# Убедись что credentials.json лежит в корне проекта
python3 scripts/create_template.py -c credentials.json -s
```

Что делает скрипт:
- Создаёт таблицу в твоём Google Drive
- Записывает все 13 колонок с заголовками
- Форматирует шапку (цвет, bold)
- Открывает доступ сервисному аккаунту (если `-s`)

После запуска ты увидишь:
```
✅ Таблица создана!
   ID: 1a2b3c4d5e6f7g8h9i0jklmnopqrstuvwxyz
   URL: https://docs.google.com/spreadsheets/d/...
```

**Скопируй ID таблицы** (длинная строка из URL).

### 7. Настройка .env

```bash
cp .env.example .env
```

Открой `.env` и заполни:

```env
# Telegram
TELEGRAM_BOT_TOKEN=123456...wxyz
ADMIN_IDS=111111111,222222222

# Google Sheets
GOOGLE_CREDENTIALS_FILE=credentials.json
SPREADSHEET_ID=1a2b3c4d5e6f7g8h9i0jklmnopqrstuvwxyz

# Опционально
REMINDER_DAYS_BEFORE=60
CHECK_INTERVAL_HOURS=1
```

**Где взять ADMIN_IDS:**
1. Открой Telegram, найди **[@userinfobot](https://t.me/userinfobot)** (или **@getidsbot**)
2. Напиши `/start`
3. Скопируй свой **ID** (число, например `123456789`)
4. Это твой admin ID — добавь в `ADMIN_IDS`

### 8. Запуск

```bash
python3 bot.py
```

Если всё настроено — увидишь:
```
🚀 Запуск Telegram-бота...
✅ Google Sheets клиент инициализирован
✅ ReminderScheduler запущен
✅ Бот авторизован. Admin IDs: [111111111]
📡 Ожидание сообщений...
```

---

## Ручное создание таблицы (без скрипта)

Если не хочешь использовать скрипт, создай таблицу вручную:

1. Открой [Google Sheets](https://sheets.google.com/)
2. Создай новую таблицу
3. Назови лист `Клиенты`
4. В первой строке добавь заголовки:

| A | B | C | D | E | F | G | H | I | J | K | L | M |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ID записи | Дата создания | Кто создал | Telegram username | Telegram ID | Контакт | Дата начала | Срок (мес) | Дата окончания | Дата напоминания | Статус | Дубль | Комментарий |

5. **Поделись** таблицей с email сервисного аккаунта (из credentials.json, поле `client_email`)
   - Нажми "Поделиться" → вставь email → роль "Редактор"

---

## Команды бота

| Команда | Кто | Описание |
|---------|-----|---------|
| `/start` | все | Приветствие + меню + автопривязка к записи |
| `/help` | все | Помощь |
| `/cancel` | все | Отменить текущее действие |
| `/clients` | админ | Список всех клиентов |
| `/stats` | админ | Статистика (всего/активных/истекающих) |
| `/check_dups` | админ | Проверить дубликаты |
| `/link` | админ | Привязать клиента к существующей записи |
| 📝 Добавить клиента | админ | Пошаговый ввод (FSM) |

---

## Как работает привязка клиента

### Автоматически (клиент нажал `/start`)

1. Клиент открывает бот → нажимает `/start`
2. Бот ищет запись с таким же username в Sheets
3. **Нашёл** → показывает данные записи → кнопки «✅ Да, это я» / «❌ Нет»
   - Клиент нажал «Да» → Telegram ID привязан, статус = «активен»
   - Клиент нажал «Нет» → может создать новую запись
4. **Не нашёл** → приветствие + кнопка «Добавить клиента»

### Вручную (админ через `/link`)

1. Админ пишет `/link`
2. Вводит username клиента (например `@ivanov`)
3. Бот показывает найденные записи с этим username
4. Админ выбирает нужную → бот привязывает клиента

---

## Добавление клиента

### Админ

Админ нажимает кнопку **«Добавить клиента»** → вводит:
1. Дата начала договора (ДД.ММ.ГГГГ)
2. Срок в месяцах (число)
3. Контакт клиента (username или телефон)

Бот сам рассчитает дату окончания и дату напоминания, запишет в Sheets.

### Клиент (сам)

Клиент пишет боту `/start` → если запись не найдена → кнопка **«Добавить клиента»** → вводит те же данные. Отличие: в поле `Кто создал` будет `client`, а не `admin`.

---

## Логика напоминаний

Это ключевая логика проекта:

| Кто добавил | Кто запускал бота | Куда уходит напоминание |
|-------------|------------------|------------------------|
| админ | клиент НЕ запускал | только админу |
| админ | клиент запускал | админу |
| клиент | клиент (сам) | админу + клиенту |

**Суть:** если клиент хотя бы раз написал боту `/start` — он «в системе» и может получать напоминания сам. Если не писал — напоминание уходит только админу (клиент не получит сообщение от бота, т.к. бот не знает его Telegram ID).

**Scheduler** проверяет таблицу каждый час (`CHECK_INTERVAL_HOURS`). Если `reminder_date` сегодня или уже прошло → отправляет напоминание according to the table above.

---

## Структура файлов

```
telegram-reminder-bot/
├── bot.py                  # Точка входа, dispatcher, роутер
├── config.py               # Все настройки из .env
├── scheduler.py            # APScheduler — проверка дат и рассылка напоминаний
├── handlers/
│   ├── common.py           # /start (автопривязка), /help, /cancel
│   ├── admin.py            # /clients, /stats, /check_dups, /link + callbacks
│   ├── client.py           # Добавление клиента (FSM), callbacks привязки
│   └── states.py           # FSM состояния BotStates
├── sheets/
│   └── client.py           # Google Sheets API (чтение/запись/поиск дублей)
├── db/
│   └── state.py            # SQLite — отметка кто запускал бота
├── scripts/
│   ├── create_template.py  # Создание таблицы в Google Drive
│   └── README.md           # Инструкция к скрипту
├── requirements.txt        # pip зависимости
├── .env.example            # Пример переменных
├── .gitignore              # Игнорируемые файлы
└── README.md               # Этот файл
```

---

## Развёртывание на сервере

### systemd service

Создай файл `/etc/systemd/system/reminder-bot.service`:

```ini
[Unit]
Description=Telegram Reminder Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/telegram-reminder-bot
ExecStart=/home/ubuntu/telegram-reminder-bot/venv/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable reminder-bot
sudo systemctl start reminder-bot
sudo systemctl status reminder-bot   # проверить
```

### Docker (опционально)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python3", "bot.py"]
```

---

## Настройки

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | — | Токен бота от @BotFather |
| `ADMIN_IDS` | — | ID админов через запятую |
| `SPREADSHEET_ID` | — | ID таблицы Google Sheets |
| `GOOGLE_CREDENTIALS_FILE` | `credentials.json` | Путь к ключу сервисного аккаунта |
| `REMINDER_DAYS_BEFORE` | `60` | За сколько дней до конца напоминать |
| `CHECK_INTERVAL_HOURS` | `1` | Как часто проверять даты (часы) |

---

## Возможные проблемы

**`credentials.json not found`**
- Убедись что файл лежит в корне проекта и имя совпадает с `GOOGLE_CREDENTIALS_FILE` в `.env`

**`Spreadsheet not found`**
- Проверь `SPREADSHEET_ID` — это длинная строка из URL таблицы
- Убедись что таблица открыта для сервисного аккаунта (email из credentials.json)

**`Bot not started`**
- Проверь `TELEGRAM_BOT_TOKEN` — не должно быть пробелов
- Убедись что бот не заблокирован через @BotFather

**Админские команды не работают**
- Проверь `ADMIN_IDS` — должны быть числовые ID, через запятую
- Узнать свой ID: напиши боту [@userinfobot](https://t.me/userinfobot)

**Бот не видит таблицу**
- Открой таблицу вручную и убедись что Service Account email имеет доступ «Редактор»

---

## Планы по доработке

- [ ] Команда `/delete_client` — удаление клиента
- [ ] Команда `/edit_client` — редактирование записи
- [ ] Веб-интерфейс для админа
- [ ] Рассылка по чатам (broadcast)
- [ ] Интеграция с расчётом потребления и показаниями счётчиков
- [ ] Юнит-тесты

---

## Лицензия

MIT
