from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.exceptions import TelegramBadRequest

from datetime import datetime, date, timedelta
import asyncio

from services.training_types import get_all_training_types, get_training_type_by_id
from services.classes import get_templates_by_training_type, get_template_by_id
from services.clients import get_client_by_telegram_id
from services.bookings import (
    booking_exists,
    has_free_slots,
    create_booking,
    get_free_slots,
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

phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Поделиться номером", request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


async def safe_answer_callback(callback: CallbackQuery):
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass


async def safe_edit_text(target_message, text: str, reply_markup=None):
    try:
        await target_message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            return
        raise


async def safe_remove_markup(target_message):
    try:
        await target_message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass


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


def get_next_7_days_slots(templates):
    today = date.today()
    result = []

    for template in templates:
        template_weekday = template["weekday"]

        for i in range(0, 7):
            slot_date = today + timedelta(days=i)
            if slot_date.weekday() == template_weekday:
                booking_date = slot_date.strftime("%Y-%m-%d")
                result.append(
                    {
                        "template_id": template["id"],
                        "training_type_name": template["training_type_name"],
                        "time": template["time"],
                        "trainer": template["trainer"],
                        "capacity": template["capacity"],
                        "booking_date": booking_date,
                    }
                )

    result.sort(key=lambda x: (x["booking_date"], x["time"]))
    return result


@router.message(F.text == "Записаться")
async def booking_start(message: Message):
    training_types = get_all_training_types(active_only=True)

    if not training_types:
        await message.answer("Сейчас нет доступных направлений.")
        return

    buttons = []
    for item in training_types:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=item["name"], callback_data=f"type:{item['id']}"
                )
            ]
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите тип тренировки:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("type:"))
async def choose_slot(callback: CallbackQuery):
    await safe_answer_callback(callback)

    training_type_id = int(callback.data.split(":", 1)[1])
    training_type = get_training_type_by_id(training_type_id)

    if not training_type or training_type["is_active"] != 1:
        await safe_edit_text(callback.message, "Такого типа тренировки нет.")
        return

    templates = get_templates_by_training_type(training_type_id)

    if not templates:
        await safe_edit_text(
            callback.message,
            f"Для направления {training_type['name']} пока нет шаблонов.",
        )
        return

    slots = get_next_7_days_slots(templates)

    buttons = []
    for slot in slots:
        free_slots = get_free_slots(slot["template_id"], slot["booking_date"])
        if free_slots <= 0:
            continue

        text = f"{format_booking_date(slot['booking_date'], slot['time'])} ({free_slots} мест)"
        callback_data = f"book:{slot['template_id']}:{slot['booking_date']}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    if not buttons:
        await safe_edit_text(
            callback.message,
            f"Вы выбрали: {training_type['name']}\n\nСвободных мест на ближайшие 7 дней нет.",
        )
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await safe_edit_text(
        callback.message,
        f"Вы выбрали: {training_type['name']}\n\nВыберите дату и время:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("book:"))
async def confirm_booking(callback: CallbackQuery):
    await safe_answer_callback(callback)

    _, template_id_str, booking_date = callback.data.split(":", 2)
    template_id = int(template_id_str)
    telegram_id = callback.from_user.id

    client = get_client_by_telegram_id(telegram_id)

    if not client or not str(client["phone"]).strip():
        await callback.message.answer(
            "Пожалуйста, сначала отправьте номер телефона для записи.",
            reply_markup=phone_keyboard,
        )
        return

    client_id = client["id"]
    await safe_remove_markup(callback.message)

    template = get_template_by_id(template_id)
    if not template or template["is_active"] != 1:
        await safe_edit_text(callback.message, "Такого шаблона нет.")
        return

    if booking_exists(client_id, template_id, booking_date):
        await safe_edit_text(callback.message, "Вы уже записаны на это занятие.")
        return

    if not has_free_slots(template_id, booking_date):
        await safe_edit_text(callback.message, "К сожалению, мест больше нет.")
        return

    loading_frames = [
        "⏳ Записываю вас на тренировку.",
        "⏳ Записываю вас на тренировку..",
        "⏳ Записываю вас на тренировку...",
    ]

    await safe_edit_text(callback.message, loading_frames[0])
    await asyncio.sleep(0.2)
    await safe_edit_text(callback.message, loading_frames[1])
    await asyncio.sleep(0.2)
    await safe_edit_text(callback.message, loading_frames[2])

    create_booking(client_id, template_id, booking_date)
    formatted_date = format_booking_date(booking_date, template["time"])

    success_text = (
        "✅ Вы успешно записаны!\n\n"
        f"{template['training_type_name']}\n"
        f"{formatted_date}\n"
        f"Тренер: {template['trainer']}"
    )

    await safe_edit_text(callback.message, success_text)
