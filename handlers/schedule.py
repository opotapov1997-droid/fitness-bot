from aiogram import Router, F
from aiogram.types import Message

from services.classes import get_all_active_templates

router = Router()

WEEKDAYS = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}


@router.message(F.text == "Расписание")
async def schedule_handler(message: Message):
    templates = get_all_active_templates()

    if not templates:
        await message.answer("Сейчас нет активных шаблонов тренировок.")
        return

    text = "Шаблоны тренировок:\n\n"

    for item in templates:
        weekday = WEEKDAYS.get(item["weekday"], str(item["weekday"]))
        text += (
            f"• {item['training_type_name']}\n"
            f"  {weekday} — {item['time']}\n"
            f"  Тренер: {item['trainer']}\n"
            f"  Мест: {item['capacity']}\n\n"
        )

    await message.answer(text)
