import sqlite3
from config import Config

def get_connection():
    conn = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица 1: Собранные объекты (Раздел 4 ТЗ)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT,
            price REAL,
            source_url TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    # Индексы для быстрого поиска (Раздел 4 ТЗ)
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_title ON items(title)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_category ON items(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_price ON items(price)')

    # Таблица 2: Журнал запусков парсера (Раздел 4 ТЗ)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parse_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            pages_processed INTEGER DEFAULT 0,
            items_added INTEGER DEFAULT 0,
            items_updated INTEGER DEFAULT 0,
            error_message TEXT
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("База данных и таблицы успешно созданы!")
