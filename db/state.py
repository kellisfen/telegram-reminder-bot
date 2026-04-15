"""
Хранилище состояний клиентов — кто запускал бота
Используем SQLite для персистентности
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "client_states.db")


class ClientStateDB:
    """SQLite база состояний клиентов"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Создаёт таблицу если нет"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS client_states (
                    telegram_id TEXT PRIMARY KEY,
                    started_bot INTEGER DEFAULT 0,
                    started_at TEXT,
                    last_seen TEXT
                )
            """)

    def mark_started(self, telegram_id: str):
        """Отмечает что клиент запускал бота"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO client_states (telegram_id, started_bot, started_at, last_seen)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    started_bot = 1,
                    last_seen = ?
            """, (telegram_id, now, now, now))

    def has_started(self, telegram_id: str) -> bool:
        """Проверяет запускал ли клиент бота"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT started_bot FROM client_states WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = cursor.fetchone()
            return bool(row and row[0])

    def get_all_started(self) -> set[str]:
        """Возвращает set всех telegram_id кто запускал бота"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT telegram_id FROM client_states WHERE started_bot = 1"
            )
            return {row[0] for row in cursor.fetchall()}
