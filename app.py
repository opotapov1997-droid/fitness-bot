import asyncio
import contextlib
from datetime import datetime, date

from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.db import init_db
from config import BOT_TOKEN
from handlers.start import router as start_router
from handlers.info import router as info_router
from handlers.schedule import router as schedule_router
from handlers.booking_flow import router as booking_flow_router
from handlers.phone_flow import router as phone_flow_router
from handlers.admin import router as admin_router
from services.bookings import get_due_reminders, mark_reminder_sent, REMINDER_HOURS_BEFORE

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start_router)
dp.include_router(info_router)
dp.include_router(phone_flow_router)
dp.include_router(schedule_router)
dp.include_router(booking_flow_router)
dp.include_router(admin_router)

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

WEEKDAYS = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"}


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


async def reminders_loop():
    while True:
        try:
            reminders = get_due_reminders()
            for item in reminders:
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text="✅ Буду",
                            callback_data=f"confirm:{item['id']}",
                        ),
                        InlineKeyboardButton(
                            text="❌ Не смогу",
                            callback_data=f"decline:{item['id']}",
                        ),
                    ]]
                )
                text = (
                    "🔔 Напоминание о тренировке"

                    f"{item['training_type_name']}"
                    f"📅 {format_booking_date(item['booking_date'], item['time'])}"
                    f"👤 Тренер: {item['trainer']}"

                    f"Пожалуйста, подтвердите участие. Напоминание отправлено за {REMINDER_HOURS_BEFORE} часов до начала."
                )
                await bot.send_message(item["telegram_id"], text, reply_markup=keyboard)
                mark_reminder_sent(item["id"])
        except Exception as e:
            print(f"Reminder loop error: {e}")

        await asyncio.sleep(60)


async def main():
    init_db()
    reminder_task = asyncio.create_task(reminders_loop())
    try:
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reminder_task


if __name__ == "__main__":
    asyncio.run(main())
