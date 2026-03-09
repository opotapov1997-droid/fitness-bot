import sqlite3

DB_NAME = "fitness_bot.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(column[1] == column_name for column in columns)


def _add_column_if_missing(cursor, table_name: str, column_name: str, ddl: str):
    if not _column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            full_name TEXT,
            phone TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS training_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS class_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            training_type_id INTEGER NOT NULL,
            weekday INTEGER NOT NULL,
            time TEXT NOT NULL,
            trainer TEXT,
            capacity INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (training_type_id) REFERENCES training_types(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            confirmed INTEGER DEFAULT 0,
            reminder_sent INTEGER DEFAULT 0,
            confirmed_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id),
            FOREIGN KEY (template_id) REFERENCES class_templates(id)
        )
        """
    )

    # Lightweight migrations for existing databases
    _add_column_if_missing(cursor, "clients", "is_admin", "is_admin INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "bookings", "confirmed", "confirmed INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "bookings", "reminder_sent", "reminder_sent INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "bookings", "confirmed_at", "confirmed_at TEXT")

    conn.commit()
    conn.close()
