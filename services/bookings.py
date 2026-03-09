from datetime import date, datetime, timedelta

from database.db import get_connection


REMINDER_HOURS_BEFORE = 12


def booking_exists(client_id, template_id, booking_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 1 FROM bookings
        WHERE client_id = ? AND template_id = ? AND booking_date = ?
        """,
        (client_id, template_id, booking_date),
    )

    row = cursor.fetchone()
    conn.close()
    return row is not None


def create_booking(client_id, template_id, booking_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO bookings (client_id, template_id, booking_date)
        VALUES (?, ?, ?)
        """,
        (client_id, template_id, booking_date),
    )

    conn.commit()
    conn.close()


def cancel_booking_by_id(client_id, booking_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM bookings
        WHERE id = ? AND client_id = ?
        """,
        (booking_id, client_id),
    )

    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted > 0


def get_booking_count(template_id, booking_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM bookings
        WHERE template_id = ? AND booking_date = ?
        """,
        (template_id, booking_date),
    )

    row = cursor.fetchone()
    conn.close()
    return row["count"]


def has_free_slots(template_id, booking_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT capacity
        FROM class_templates
        WHERE id = ? AND is_active = 1
        """,
        (template_id,),
    )
    template_row = cursor.fetchone()

    if not template_row:
        conn.close()
        return False

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM bookings
        WHERE template_id = ? AND booking_date = ?
        """,
        (template_id, booking_date),
    )
    booking_row = cursor.fetchone()

    conn.close()
    return booking_row["count"] < template_row["capacity"]


def get_free_slots(template_id, booking_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT capacity
        FROM class_templates
        WHERE id = ?
        """,
        (template_id,),
    )
    template_row = cursor.fetchone()

    if not template_row:
        conn.close()
        return 0

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM bookings
        WHERE template_id = ? AND booking_date = ?
        """,
        (template_id, booking_date),
    )
    booking_row = cursor.fetchone()

    conn.close()
    return max(template_row["capacity"] - booking_row["count"], 0)


def get_user_bookings(client_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            b.id,
            b.booking_date,
            b.confirmed,
            ct.id AS template_id,
            ct.time,
            ct.trainer,
            tt.name AS training_type_name
        FROM bookings b
        JOIN class_templates ct ON b.template_id = ct.id
        JOIN training_types tt ON ct.training_type_id = tt.id
        WHERE b.client_id = ?
        ORDER BY b.booking_date, ct.time
        """,
        (client_id,),
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def template_has_bookings(template_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM bookings
        WHERE template_id = ?
        """,
        (template_id,),
    )

    row = cursor.fetchone()
    conn.close()
    return row["count"] > 0


def get_bookings_for_admin(days_ahead: int = 7):
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today().strftime("%Y-%m-%d")
    end_day = (date.today() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    cursor.execute(
        """
        SELECT
            b.booking_date,
            ct.id AS template_id,
            ct.time,
            ct.trainer,
            ct.capacity,
            tt.name AS training_type_name,
            COUNT(b.id) AS booked_count,
            SUM(CASE WHEN b.confirmed = 1 THEN 1 ELSE 0 END) AS confirmed_count
        FROM bookings b
        JOIN class_templates ct ON b.template_id = ct.id
        JOIN training_types tt ON ct.training_type_id = tt.id
        WHERE b.booking_date BETWEEN ? AND ?
        GROUP BY b.booking_date, ct.id, ct.time, ct.trainer, ct.capacity, tt.name
        ORDER BY b.booking_date, ct.time
        """,
        (today, end_day),
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_booked_clients_for_slot(template_id, booking_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            b.id,
            c.full_name,
            c.phone,
            b.confirmed
        FROM bookings b
        JOIN clients c ON b.client_id = c.id
        WHERE b.template_id = ? AND b.booking_date = ?
        ORDER BY c.full_name
        """,
        (template_id, booking_date),
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_client_telegram_ids_for_slot(template_id, booking_date):
    """
    Все telegram_id клиентов, записанных на конкретный слот.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT c.telegram_id
        FROM bookings b
        JOIN clients c ON b.client_id = c.id
        WHERE b.template_id = ? AND b.booking_date = ? AND c.telegram_id IS NOT NULL
        """,
        (template_id, booking_date),
    )

    rows = cursor.fetchall()
    conn.close()
    return [row["telegram_id"] for row in rows if row["telegram_id"] is not None]


def get_bookings_with_telegram_for_slot(template_id, booking_date):
    """
    Все записи на слот с telegram_id для запроса подтверждения.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            b.id,
            b.booking_date,
            b.confirmed,
            c.telegram_id,
            ct.time,
            ct.trainer,
            tt.name AS training_type_name
        FROM bookings b
        JOIN clients c ON b.client_id = c.id
        JOIN class_templates ct ON b.template_id = ct.id
        JOIN training_types tt ON ct.training_type_id = tt.id
        WHERE b.template_id = ? AND b.booking_date = ? AND c.telegram_id IS NOT NULL
        """,
        (template_id, booking_date),
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_due_reminders(hours_before: int = REMINDER_HOURS_BEFORE):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            b.id,
            b.booking_date,
            b.reminder_sent,
            c.telegram_id,
            ct.id AS template_id,
            ct.time,
            ct.trainer,
            tt.name AS training_type_name
        FROM bookings b
        JOIN clients c ON b.client_id = c.id
        JOIN class_templates ct ON b.template_id = ct.id
        JOIN training_types tt ON ct.training_type_id = tt.id
        WHERE b.reminder_sent = 0
        """
    )

    rows = cursor.fetchall()
    conn.close()

    due = []
    now = datetime.now()
    for row in rows:
        slot_dt = datetime.strptime(f"{row['booking_date']} {row['time']}", "%Y-%m-%d %H:%M")
        delta_hours = (slot_dt - now).total_seconds() / 3600
        if 0 <= delta_hours <= hours_before:
            due.append(row)
    return due


def mark_reminder_sent(booking_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET reminder_sent = 1 WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()


def mark_confirmed(booking_id, client_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE bookings
        SET confirmed = 1, confirmed_at = CURRENT_TIMESTAMP
        WHERE id = ? AND client_id = ?
        """,
        (booking_id, client_id),
    )
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    return updated > 0


def get_booking_by_id(booking_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            b.id,
            b.client_id,
            b.template_id,
            b.booking_date,
            b.confirmed,
            ct.time,
            ct.trainer,
            tt.name AS training_type_name
        FROM bookings b
        JOIN class_templates ct ON b.template_id = ct.id
        JOIN training_types tt ON ct.training_type_id = tt.id
        WHERE b.id = ?
        """,
        (booking_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def get_total_bookings():
    """
    Общее количество записей.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM bookings")
    row = cursor.fetchone()

    conn.close()
    return row["count"] if row else 0


def get_total_confirmed_bookings():
    """
    Общее количество подтверждённых записей.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM bookings WHERE confirmed = 1")
    row = cursor.fetchone()

    conn.close()
    return row["count"] if row else 0


def get_bookings_last_days(days: int):
    """
    Количество записей за последние N дней.
    """
    conn = get_connection()
    cursor = conn.cursor()

    start_date = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM bookings
        WHERE booking_date >= ?
        """,
        (start_date,),
    )
    row = cursor.fetchone()

    conn.close()
    return row["count"] if row else 0
