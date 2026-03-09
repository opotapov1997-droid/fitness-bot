from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Расписание"), KeyboardButton(text="Записаться")],
        [KeyboardButton(text="Мои записи"), KeyboardButton(text="Цены")],
        [KeyboardButton(text="FAQ"), KeyboardButton(text="Контакты")],
    ],
    resize_keyboard=True,
)

