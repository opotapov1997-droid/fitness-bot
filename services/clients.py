from database.db import get_connection


def get_client_by_telegram_id(telegram_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM clients WHERE telegram_id = ?",
        (telegram_id,),
    )
    row = cursor.fetchone()

    conn.close()
    return row


def create_or_update_client(telegram_id, full_name, phone):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM clients WHERE telegram_id = ?",
        (telegram_id,),
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            """
            UPDATE clients
            SET full_name = ?, phone = ?
            WHERE telegram_id = ?
            """,
            (full_name, phone, telegram_id),
        )
    else:
        cursor.execute(
            """
            INSERT INTO clients (telegram_id, full_name, phone)
            VALUES (?, ?, ?)
            """,
            (telegram_id, full_name, phone),
        )

    conn.commit()
    conn.close()


def get_all_clients():
    """
    Возвращает всех клиентов для админ-панели.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, telegram_id, full_name, phone, is_admin, created_at
        FROM clients
        ORDER BY created_at DESC
        """
    )
    rows = cursor.fetchall()

    conn.close()
    return rows


def get_clients_count():
    """
    Общее количество клиентов.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM clients")
    row = cursor.fetchone()

    conn.close()
    return row["count"] if row else 0


def get_all_client_telegram_ids():
    """
    Все telegram_id клиентов для рассылки.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT telegram_id
        FROM clients
        WHERE telegram_id IS NOT NULL
        """
    )
    rows = cursor.fetchall()

    conn.close()
    return [row["telegram_id"] for row in rows if row["telegram_id"] is not None]


def get_admin_clients():
    """
    Список клиентов с правами админа.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, telegram_id, full_name, phone, is_admin, created_at
        FROM clients
        WHERE is_admin = 1
        ORDER BY created_at DESC
        """
    )
    rows = cursor.fetchall()

    conn.close()
    return rows


def set_client_admin(client_id: int, is_admin: bool):
    """
    Установить/снять флаг админа у клиента.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE clients SET is_admin = ? WHERE id = ?",
        (1 if is_admin else 0, client_id),
    )
    conn.commit()
    conn.close()