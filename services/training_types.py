from database.db import get_connection


def get_all_training_types(active_only: bool = True):
    conn = get_connection()
    cursor = conn.cursor()

    if active_only:
        cursor.execute(
            """
            SELECT * FROM training_types
            WHERE is_active = 1
            ORDER BY name
            """
        )
    else:
        cursor.execute("SELECT * FROM training_types ORDER BY name")

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_training_type_by_id(training_type_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM training_types WHERE id = ?", (training_type_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def create_training_type(name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO training_types (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


def deactivate_training_type(training_type_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE training_types SET is_active = 0 WHERE id = ?", (training_type_id,))
    conn.commit()
    conn.close()


def restore_training_type(training_type_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE training_types SET is_active = 1 WHERE id = ?", (training_type_id,))
    conn.commit()
    conn.close()


def delete_training_type(training_type_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM training_types WHERE id = ?", (training_type_id,))
    deleted = cursor.rowcount

    conn.commit()
    conn.close()
    return deleted > 0
