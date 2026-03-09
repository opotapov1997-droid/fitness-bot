from database.db import get_connection


def get_all_active_templates():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            ct.*,
            tt.name AS training_type_name
        FROM class_templates ct
        JOIN training_types tt ON ct.training_type_id = tt.id
        WHERE ct.is_active = 1 AND tt.is_active = 1
        ORDER BY tt.name, ct.weekday, ct.time
        """
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_inactive_templates():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            ct.*,
            tt.name AS training_type_name
        FROM class_templates ct
        JOIN training_types tt ON ct.training_type_id = tt.id
        WHERE ct.is_active = 0 AND tt.is_active = 1
        ORDER BY tt.name, ct.weekday, ct.time
        """
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_template_by_id(template_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            ct.*,
            tt.name AS training_type_name
        FROM class_templates ct
        JOIN training_types tt ON ct.training_type_id = tt.id
        WHERE ct.id = ?
        """,
        (template_id,),
    )

    row = cursor.fetchone()
    conn.close()
    return row


def get_templates_by_training_type(training_type_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            ct.*,
            tt.name AS training_type_name
        FROM class_templates ct
        JOIN training_types tt ON ct.training_type_id = tt.id
        WHERE ct.training_type_id = ?
          AND ct.is_active = 1
          AND tt.is_active = 1
        ORDER BY ct.weekday, ct.time
        """,
        (training_type_id,),
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def create_template(training_type_id, weekday, time, trainer, capacity):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO class_templates (training_type_id, weekday, time, trainer, capacity)
        VALUES (?, ?, ?, ?, ?)
        """,
        (training_type_id, weekday, time, trainer, capacity),
    )

    conn.commit()
    conn.close()


def deactivate_template(template_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE class_templates
        SET is_active = 0
        WHERE id = ?
        """,
        (template_id,),
    )

    conn.commit()
    conn.close()


def restore_template(template_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE class_templates
        SET is_active = 1
        WHERE id = ?
        """,
        (template_id,),
    )

    conn.commit()
    conn.close()


def delete_template(template_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM class_templates
        WHERE id = ?
        """,
        (template_id,),
    )

    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted > 0
