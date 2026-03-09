import gspread
from datetime import datetime

from config import GOOGLE_SHEET_NAME


def get_classes_sheet():
    gc = gspread.service_account(filename="credentials.json")
    spreadsheet = gc.open(GOOGLE_SHEET_NAME)
    worksheet = spreadsheet.worksheet("Classes")
    return worksheet


def get_active_classes():
    worksheet = get_classes_sheet()
    records = worksheet.get_all_records()

    active_classes = []

    for row in records:
        is_active = str(row.get("is_active", "")).strip().upper()

        if is_active == "TRUE":
            active_classes.append(row)

    return active_classes


def get_unique_titles():
    classes = get_active_classes()

    titles = []
    seen = set()

    for row in classes:
        title = str(row.get("title", "")).strip()

        if title and title not in seen:
            seen.add(title)
            titles.append(title)

    return titles


def get_classes_by_title(title):
    classes = get_active_classes()
    title = str(title).strip()

    result = []

    for row in classes:
        row_title = str(row.get("title", "")).strip()

        if row_title == title:
            result.append(row)

    return result


def add_booking(telegram_id, class_id, name, phone):
    gc = gspread.service_account(filename="credentials.json")
    spreadsheet = gc.open(GOOGLE_SHEET_NAME)
    worksheet = spreadsheet.worksheet("Bookings")

    records = worksheet.get_all_records()
    booking_id = len(records) + 1

    worksheet.append_row([
        booking_id,
        telegram_id,
        class_id,
        name,
        phone,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ])


def booking_exists(telegram_id, class_id):
    gc = gspread.service_account(filename="credentials.json")
    spreadsheet = gc.open(GOOGLE_SHEET_NAME)
    worksheet = spreadsheet.worksheet("Bookings")

    records = worksheet.get_all_records()

    telegram_id = str(telegram_id).strip()
    class_id = str(class_id).strip()

    for row in records:
        row_telegram_id = str(row.get("telegram_id", "")).strip()
        row_class_id = str(row.get("class_id", "")).strip()

        if row_telegram_id == telegram_id and row_class_id == class_id:
            return True

    return False


def class_exists(class_id):
    classes = get_active_classes()
    class_id = str(class_id).strip()

    for row in classes:
        row_class_id = str(row.get("class_id", "")).strip()

        if row_class_id == class_id:
            return True

    return False


def get_booking_count(class_id):
    gc = gspread.service_account(filename="credentials.json")
    spreadsheet = gc.open(GOOGLE_SHEET_NAME)
    worksheet = spreadsheet.worksheet("Bookings")

    records = worksheet.get_all_records()
    class_id = str(class_id).strip()

    count = 0

    for row in records:
        row_class_id = str(row.get("class_id", "")).strip()
        if row_class_id == class_id:
            count += 1

    return count


def get_class_capacity(class_id):
    classes = get_active_classes()
    class_id = str(class_id).strip()

    for row in classes:
        row_class_id = str(row.get("class_id", "")).strip()
        if row_class_id == class_id:
            return int(row.get("capacity", 0))

    return 0


def has_free_slots(class_id):
    booking_count = get_booking_count(class_id)
    capacity = get_class_capacity(class_id)

    return booking_count < capacity


def get_user_bookings(telegram_id):
    gc = gspread.service_account(filename="credentials.json")
    spreadsheet = gc.open(GOOGLE_SHEET_NAME)

    bookings_ws = spreadsheet.worksheet("Bookings")
    classes_ws = spreadsheet.worksheet("Classes")

    bookings = bookings_ws.get_all_records()
    classes = classes_ws.get_all_records()

    telegram_id = str(telegram_id).strip()

    user_bookings = []
    class_map = {}

    for item in classes:
        class_map[str(item.get("class_id", "")).strip()] = item

    for row in bookings:
        row_telegram_id = str(row.get("telegram_id", "")).strip()
        row_class_id = str(row.get("class_id", "")).strip()

        if row_telegram_id == telegram_id and row_class_id in class_map:
            user_bookings.append(class_map[row_class_id])

    return user_bookings


def cancel_booking(telegram_id, class_id):
    gc = gspread.service_account(filename="credentials.json")
    spreadsheet = gc.open(GOOGLE_SHEET_NAME)
    worksheet = spreadsheet.worksheet("Bookings")

    records = worksheet.get_all_records()

    telegram_id = str(telegram_id).strip()
    class_id = str(class_id).strip()

    for index, row in enumerate(records, start=2):
        row_telegram_id = str(row.get("telegram_id", "")).strip()
        row_class_id = str(row.get("class_id", "")).strip()

        if row_telegram_id == telegram_id and row_class_id == class_id:
            worksheet.delete_rows(index)
            return True

    return False


def get_client_by_telegram_id(telegram_id):
    gc = gspread.service_account(filename="credentials.json")
    spreadsheet = gc.open(GOOGLE_SHEET_NAME)
    worksheet = spreadsheet.worksheet("Clients")

    records = worksheet.get_all_records()
    telegram_id = str(telegram_id).strip()

    for row in records:
        row_telegram_id = str(row.get("telegram_id", "")).strip()
        if row_telegram_id == telegram_id:
            return row

    return None


def save_client(telegram_id, full_name, phone):
    gc = gspread.service_account(filename="credentials.json")
    spreadsheet = gc.open(GOOGLE_SHEET_NAME)
    worksheet = spreadsheet.worksheet("Clients")

    existing = get_client_by_telegram_id(telegram_id)

    if existing:
        records = worksheet.get_all_records()
        for index, row in enumerate(records, start=2):
            row_telegram_id = str(row.get("telegram_id", "")).strip()
            if row_telegram_id == str(telegram_id).strip():
                worksheet.update(f"B{index}:D{index}", [[
                    full_name,
                    phone,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]])
                return

    worksheet.append_row([
        telegram_id,
        full_name,
        phone,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ])


def get_free_slots(class_id):
    capacity = get_class_capacity(class_id)
    booked = get_booking_count(class_id)
    free_slots = capacity - booked

    if free_slots < 0:
        free_slots = 0

    return free_slots