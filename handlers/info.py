from datetime import datetime, date

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from services.clients import get_client_by_telegram_id
from services.bookings import (
    get_user_bookings,
    cancel_booking_by_id,
    mark_confirmed,
    get_booking_by_id,
)

router = Router()

MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

WEEKDAYS = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}


def format_booking_date(date_string: str, time_string: str) -> str:
    date_obj = datetime.strptime(date_string, "%Y-%m-%d").date()
    today = date.today()

    if date_obj == today:
        date_part = "Сегодня"
    elif (date_obj - today).days == 1:
        date_part = "Завтра"
    else:
        weekday = WEEKDAYS[date_obj.weekday()]
        day = date_obj.day
        month = MONTHS[date_obj.month]
        date_part = f"{weekday} {day} {month}"

    return f"{date_part} — {time_string}"


@router.message(F.text == "Цены")
async def prices_handler(message: Message):
    await message.answer(
        "Цены:"
        "• Пробное занятие — 20 лв"
        "• Разовое занятие — 25 лв"
        "• 8 занятий — 140 лв"
        "• 12 занятий — 180 лв"
    )


@router.message(F.text == "FAQ")
async def faq_handler(message: Message):
    await message.answer(
        "FAQ:"
        "• Что взять с собой? — Удобную форму и воду."
        "• Можно ли новичкам? — Да."
        "• Как отменить запись? — Через раздел 'Мои записи'."
    )


@router.message(F.text == "Контакты")
async def contacts_handler(message: Message):
    await message.answer(
        "Контакты студии:"
        "Телефон: +359 ..."
        "Instagram: ..."
        "Telegram: ..."
    )


@router.message(F.text == "Мои записи")
async def my_bookings_handler(message: Message):
    client = get_client_by_telegram_id(message.from_user.id)

    if not client:
        await message.answer("У вас пока нет активных записей.")
        return

    bookings = get_user_bookings(client["id"])

    if not bookings:
        await message.answer("У вас пока нет активных записей.")
        return

    for item in bookings:
        buttons = [[InlineKeyboardButton(text="Отменить запись", callback_data=f"cancel:{item['id']}")]]
        if item["confirmed"] == 0:
            buttons.append([
                InlineKeyboardButton(text="✅ Буду", callback_data=f"confirm:{item['id']}"),
                InlineKeyboardButton(text="❌ Не смогу", callback_data=f"decline:{item['id']}"),
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        status = "✅ Подтверждено" if item["confirmed"] == 1 else "⏳ Ждём подтверждение"

        text = (
            f"• {format_booking_date(item['booking_date'], item['time'])} — {item['training_type_name']}"
            f"👤 Тренер: {item['trainer']}"
            f"Статус: {status}"
        )

        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("cancel:"))
async def cancel_booking_handler(callback: CallbackQuery):
    await callback.answer()

    booking_id = int(callback.data.split(":", 1)[1])
    client = get_client_by_telegram_id(callback.from_user.id)

    if not client:
        await callback.message.edit_text("Не удалось найти ваш профиль.")
        return

    success = cancel_booking_by_id(client["id"], booking_id)

    if success:
        await callback.message.edit_text("Запись отменена.")
    else:
        await callback.message.edit_text("Не удалось найти такую запись.")


@router.callback_query(F.data.startswith("confirm:"))
async def confirm_presence_handler(callback: CallbackQuery):
    await callback.answer()

    booking_id = int(callback.data.split(":", 1)[1])
    client = get_client_by_telegram_id(callback.from_user.id)

    if not client:
        await callback.message.edit_text("Не удалось найти ваш профиль.")
        return

    booking = get_booking_by_id(booking_id)
    if not booking:
        await callback.message.edit_text("Запись не найдена.")
        return

    success = mark_confirmed(booking_id, client["id"])
    if not success:
        await callback.message.edit_text("Не удалось подтвердить присутствие.")
        return

    await callback.message.edit_text(
        "✅ Участие подтверждено!"
        f"{booking['training_type_name']}"
        f"📅 {format_booking_date(booking['booking_date'], booking['time'])}"
        f"👤 Тренер: {booking['trainer']}"
        "Отлично, ждём вас на тренировке 💪"
    )


@router.callback_query(F.data.startswith("decline:"))
async def decline_presence_handler(callback: CallbackQuery):
    await callback.answer()

    booking_id = int(callback.data.split(":", 1)[1])
    client = get_client_by_telegram_id(callback.from_user.id)

    if not client:
        await callback.message.edit_text("Не удалось найти ваш профиль.")
        return

    booking = get_booking_by_id(booking_id)
    if not booking:
        await callback.message.edit_text("Запись уже неактуальна.")
        return

    success = cancel_booking_by_id(client["id"], booking_id)
    if not success:
        await callback.message.edit_text("Не удалось отменить запись.")
        return

    await callback.message.edit_text(
        "❌ Запись отменена по вашему ответу."
        f"{booking['training_type_name']}"
        f"📅 {format_booking_date(booking['booking_date'], booking['time'])}"
        "Если планы изменятся, вы сможете записаться снова."
    )
