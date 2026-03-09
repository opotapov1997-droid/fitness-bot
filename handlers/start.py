from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.main_menu import main_menu

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! Я бот фитнес-студии 💪\n"
        "Здесь можно посмотреть расписание, записаться на тренировку и найти нужную информацию.",
        reply_markup=main_menu,
    )