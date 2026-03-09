from aiogram import Router, F
from aiogram.types import Message

from services.clients import create_or_update_client
from keyboards.main_menu import main_menu
from keyboards.common import phone_keyboard

router = Router()


@router.message(F.contact)
async def contact_handler(message: Message):
    phone = message.contact.phone_number
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name

    create_or_update_client(telegram_id, full_name, phone)

    await message.answer(
        "Номер телефона сохранён ✅\nТеперь можно снова выбрать запись на тренировку.",
        reply_markup=main_menu
    )