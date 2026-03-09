from database.db import get_connection

conn = get_connection()
cursor = conn.cursor()

classes = [
    ("Stretching", "2026-03-08", "18:00", "Anna", "Varna Studio", 10, 1),
    ("Fitness", "2026-03-08", "19:00", "Irina", "Varna Studio", 8, 1),
    ("Pilates", "2026-03-09", "10:00", "Anna", "Varna Studio", 12, 1),
    ("Stretching", "2026-03-10", "18:30", "Irina", "Varna Studio", 10, 1),
]

cursor.executemany("""
    INSERT INTO classes (title, date, time, trainer, location, capacity, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", classes)

conn.commit()
conn.close()

print("Тестовые тренировки добавлены")