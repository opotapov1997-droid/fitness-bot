from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from config import ADMIN_IDS
from keyboards import main_menu
from services.bookings import (
    get_booked_clients_for_slot,
    get_bookings_for_admin,
    get_bookings_last_days,
    get_client_telegram_ids_for_slot,
    get_bookings_with_telegram_for_slot,
    get_total_bookings,
    get_total_confirmed_bookings,
    template_has_bookings,
)
from services.classes import (
    create_template,
    deactivate_template,
    delete_template,
    get_all_active_templates,
    get_all_inactive_templates,
    get_template_by_id,
    restore_template,
)
from services.clients import (
    get_admin_clients,
    get_all_clients,
    get_all_client_telegram_ids,
    get_client_by_telegram_id,
    get_clients_count,
    set_client_admin,
)
from services.training_types import (
    create_training_type,
    deactivate_training_type,
    delete_training_type,
    get_all_training_types,
    restore_training_type,
)

router = Router()


class AddTrainingType(StatesGroup):
    name = State()


class AddTemplate(StatesGroup):
    weekday = State()
    time = State()
    trainer = State()
    capacity = State()


class Broadcast(StatesGroup):
    text = State()


class BroadcastSlot(StatesGroup):
    text = State()


admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить тип тренировки")],
        [KeyboardButton(text="➕ Добавить шаблон")],
        [KeyboardButton(text="📋 Типы тренировок")],
        [KeyboardButton(text="📋 Шаблоны тренировок")],
        [KeyboardButton(text="🗂 Архив шаблонов")],
        [KeyboardButton(text="👥 Кто записан")],
        [KeyboardButton(text="👥 Пользователи")],
        [KeyboardButton(text="👑 Администраторы")],
        [KeyboardButton(text="📢 Рассылка")],
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="❌ Отмена")],
        [KeyboardButton(text="⬅️ Выйти из админки")],
    ],
    resize_keyboard=True,
)

WEEKDAYS = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"}


def is_admin(user_id: int) -> bool:
    """
    Админ — это либо ID из ADMIN_IDS (суперадмин),
    либо пользователь с флагом is_admin в таблице clients.
    """
    if user_id in ADMIN_IDS:
        return True

    client = get_client_by_telegram_id(user_id)
    return bool(client and client["is_admin"] == 1)


def format_slot_date(date_string: str, time_string: str) -> str:
    date_obj = datetime.strptime(date_string, "%Y-%m-%d")
    return f"{WEEKDAYS[date_obj.weekday()]} {date_obj.day:02d}.{date_obj.month:02d} — {time_string}"


@router.message(F.text.in_(["Отмена", "отмена", "/cancel"]))
async def cancel_any_admin_flow(message: Message, state: FSMContext):
    """
    Универсальная отмена для состояний внутри админки (и не только).
    """
    current_state = await state.get_state()
    if not current_state:
        await message.answer("Сейчас нечего отменять.")
        return

    await state.clear()

    if is_admin(message.from_user.id):
        await message.answer("Действие отменено. Вы в админ-панели.", reply_markup=admin_menu)
    else:
        await message.answer("Действие отменено.", reply_markup=main_menu)


@router.message(Command("admin"))
async def admin_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админке.")
        return
    await message.answer("Админ-панель открыта.", reply_markup=admin_menu)


@router.message(F.text == "📋 Типы тренировок")
async def show_training_types(message: Message):
    if not is_admin(message.from_user.id):
        return
    training_types = get_all_training_types(active_only=False)
    if not training_types:
        await message.answer("Нет типов тренировок.")
        return

    for item in training_types:
        status = "активен" if item["is_active"] == 1 else "отключён"
        text = f"ID {item['id']} — {item['name']} ({status})"

        buttons = []
        if item["is_active"] == 1:
            buttons.append(
                InlineKeyboardButton(
                    text="⏸ Отключить",
                    callback_data=f"tt_disable:{item['id']}",
                )
            )
        else:
            buttons.append(
                InlineKeyboardButton(
                    text="♻️ Включить",
                    callback_data=f"tt_restore:{item['id']}",
                )
            )

        buttons.append(
            InlineKeyboardButton(
                text="🗑 Удалить",
                callback_data=f"tt_delete:{item['id']}",
            )
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("tt_disable:"))
async def training_type_disable(callback: CallbackQuery):
    await callback.answer()
    type_id = int(callback.data.split(":")[1])
    deactivate_training_type(type_id)
    await callback.message.edit_text("Тип тренировки отключён.")


@router.callback_query(F.data.startswith("tt_restore:"))
async def training_type_restore(callback: CallbackQuery):
    await callback.answer()
    type_id = int(callback.data.split(":")[1])
    restore_training_type(type_id)
    await callback.message.edit_text("Тип тренировки снова активен.")


@router.callback_query(F.data.startswith("tt_delete:"))
async def training_type_delete(callback: CallbackQuery):
    await callback.answer()
    type_id = int(callback.data.split(":")[1])

    # Нельзя удалить тип, если есть шаблоны на нём
    from services.classes import get_templates_by_training_type  # локальный импорт чтобы избежать циклов

    templates = get_templates_by_training_type(type_id)
    if templates:
        await callback.message.edit_text(
            "Нельзя удалить тип тренировки, потому что по нему есть шаблоны.\n"
            "Сначала удалите или отключите шаблоны."
        )
        return

    success = delete_training_type(type_id)
    await callback.message.edit_text("Тип тренировки удалён." if success else "Не удалось удалить тип тренировки.")


@router.message(F.text == "📋 Шаблоны тренировок")
async def show_templates(message: Message):
    if not is_admin(message.from_user.id):
        return
    templates = get_all_active_templates()
    if not templates:
        await message.answer("Нет активных шаблонов тренировок.")
        return

    for item in templates:
        weekday = WEEKDAYS.get(item["weekday"], str(item["weekday"]))
        text = (
            f"ID {item['id']} — {item['training_type_name']}\n"
            f"{weekday} — {item['time']}\n"
            f"Тренер: {item['trainer']}\n"
            f"Мест: {item['capacity']}"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⏸ Отключить", callback_data=f"template_disable:{item['id']}"),
                    InlineKeyboardButton(text="🗑 Удалить", callback_data=f"template_delete:{item['id']}"),
                ]
            ]
        )
        await message.answer(text, reply_markup=keyboard)


@router.message(F.text == "🗂 Архив шаблонов")
async def show_archived_templates(message: Message):
    if not is_admin(message.from_user.id):
        return
    templates = get_all_inactive_templates()
    if not templates:
        await message.answer("Архив шаблонов пуст.")
        return

    for item in templates:
        weekday = WEEKDAYS.get(item["weekday"], str(item["weekday"]))
        text = (
            f"ID {item['id']} — {item['training_type_name']}\n"
            f"{weekday} — {item['time']}\n"
            f"Тренер: {item['trainer']}\n"
            f"Мест: {item['capacity']}"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="♻️ Включить обратно", callback_data=f"template_restore:{item['id']}")]
            ]
        )
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("template_disable:"))
async def disable_template_handler(callback: CallbackQuery):
    await callback.answer()
    template_id = int(callback.data.split(":")[1])
    template = get_template_by_id(template_id)
    if not template:
        await callback.message.edit_text("Шаблон не найден.")
        return
    deactivate_template(template_id)
    await callback.message.edit_text("Шаблон отключён и отправлен в архив.")


@router.callback_query(F.data.startswith("template_restore:"))
async def restore_template_handler(callback: CallbackQuery):
    await callback.answer()
    template_id = int(callback.data.split(":")[1])
    template = get_template_by_id(template_id)
    if not template:
        await callback.message.edit_text("Шаблон не найден.")
        return
    restore_template(template_id)
    await callback.message.edit_text("Шаблон снова активен.")


@router.callback_query(F.data.startswith("template_delete:"))
async def delete_template_handler(callback: CallbackQuery):
    await callback.answer()
    template_id = int(callback.data.split(":")[1])
    template = get_template_by_id(template_id)
    if not template:
        await callback.message.edit_text("Шаблон не найден.")
        return
    if template_has_bookings(template_id):
        await callback.message.edit_text(
            "Нельзя удалить шаблон, потому что по нему уже есть записи.\n"
            "Можно только отключить его."
        )
        return
    success = delete_template(template_id)
    await callback.message.edit_text("Шаблон удалён." if success else "Не удалось удалить шаблон.")


@router.message(F.text == "➕ Добавить тип тренировки")
async def add_type_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "Введите название типа тренировки:\n\n"
        "Чтобы отменить и вернуться в меню, отправьте «Отмена» или /cancel."
    )
    await state.set_state(AddTrainingType.name)


@router.message(AddTrainingType.name)
async def add_type_name(message: Message, state: FSMContext):
    name = message.text.strip()
    create_training_type(name)
    await message.answer(f"Тип тренировки '{name}' успешно создан.", reply_markup=admin_menu)
    await state.clear()


@router.message(F.text == "➕ Добавить шаблон")
async def add_template_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    training_types = get_all_training_types(active_only=True)
    if not training_types:
        await message.answer("Сначала создайте тип тренировки.")
        return
    buttons = []
    for item in training_types:
        buttons.append([
            InlineKeyboardButton(text=item["name"], callback_data=f"template_type:{item['id']}")
        ])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите тип тренировки:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("template_type:"))
async def template_choose_type(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    training_type_id = int(callback.data.split(":")[1])
    await state.update_data(training_type_id=training_type_id)
    buttons = [[InlineKeyboardButton(text=WEEKDAYS[i], callback_data=f"weekday:{i}")] for i in range(7)]
    await callback.message.edit_text("Выберите день недели:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(AddTemplate.weekday)


@router.callback_query(F.data.startswith("weekday:"), AddTemplate.weekday)
async def template_weekday(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    weekday = int(callback.data.split(":")[1])
    await state.update_data(weekday=weekday)
    await callback.message.edit_text("Введите время (например 18:00):")
    await state.set_state(AddTemplate.time)


@router.message(AddTemplate.time)
async def template_time(message: Message, state: FSMContext):
    await state.update_data(time=message.text.strip())
    await message.answer("Введите имя тренера:")
    await state.set_state(AddTemplate.trainer)


@router.message(AddTemplate.trainer)
async def template_trainer(message: Message, state: FSMContext):
    await state.update_data(trainer=message.text.strip())
    await message.answer("Введите количество мест:")
    await state.set_state(AddTemplate.capacity)


@router.message(AddTemplate.capacity)
async def template_capacity(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Количество мест должно быть числом. Введите ещё раз:")
        return

    data = await state.get_data()
    create_template(
        training_type_id=data["training_type_id"],
        weekday=data["weekday"],
        time=data["time"],
        trainer=data["trainer"],
        capacity=int(message.text),
    )
    await message.answer("Шаблон тренировки успешно создан.", reply_markup=admin_menu)
    await state.clear()


@router.message(F.text == "👥 Кто записан")
async def admin_bookings_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    slots = get_bookings_for_admin(days_ahead=7)
    if not slots:
        await message.answer("На ближайшие 7 дней записей нет.")
        return

    for item in slots:
        text = (
            f"{item['training_type_name']}\n"
            f"{format_slot_date(item['booking_date'], item['time'])}\n"
            f"Тренер: {item['trainer']}\n"
            f"Записано: {item['booked_count']} / {item['capacity']}\n"
            f"Подтвердили: {item['confirmed_count']}"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Показать список",
                        callback_data=f"admin_slot:{item['template_id']}:{item['booking_date']}",
                    ),
                    InlineKeyboardButton(
                        text="📢 Рассылка по этому слоту",
                        callback_data=f"admin_slot_broadcast:{item['template_id']}:{item['booking_date']}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="❓ Запросить готовность",
                        callback_data=f"admin_slot_ask:{item['template_id']}:{item['booking_date']}",
                    ),
                ]
            ]
        )
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("admin_slot:"))
async def admin_slot_details(callback: CallbackQuery):
    await callback.answer()
    _, template_id_str, booking_date = callback.data.split(":", 2)
    template_id = int(template_id_str)
    clients = get_booked_clients_for_slot(template_id, booking_date)
    template = get_template_by_id(template_id)

    if not template:
        await callback.message.answer("Шаблон не найден.")
        return

    if not clients:
        await callback.message.answer("На этот слот записей нет.")
        return

    lines = [
        f"{template['training_type_name']}\n{format_slot_date(booking_date, template['time'])}\n"
    ]
    for idx, item in enumerate(clients, start=1):
        status = "✅" if item["confirmed"] == 1 else "⏳"
        phone = item["phone"] or "—"
        lines.append(f"{idx}. {item['full_name']} {status}\n   {phone}")

    await callback.message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("admin_slot_ask:"))
async def admin_slot_ask_confirmations(callback: CallbackQuery):
    await callback.answer()
    _, template_id_str, booking_date = callback.data.split(":", 2)
    template_id = int(template_id_str)

    rows = get_bookings_with_telegram_for_slot(template_id, booking_date)
    if not rows:
        await callback.message.answer("На этот слот нет записей для запроса подтверждения.")
        return

    sent = 0
    skipped_confirmed = 0

    for row in rows:
        if row["confirmed"] == 1:
            skipped_confirmed += 1
            continue

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Буду",
                        callback_data=f"confirm:{row['id']}",
                    ),
                    InlineKeyboardButton(
                        text="❌ Не смогу",
                        callback_data=f"decline:{row['id']}",
                    ),
                ]
            ]
        )

        text = (
            "❓ Подтвердите участие в тренировке\n\n"
            f"{row['training_type_name']}\n"
            f"{format_slot_date(row['booking_date'], row['time'])}\n"
            f"👤 Тренер: {row['trainer']}\n\n"
            "Пожалуйста, нажмите одну из кнопок ниже."
        )

        try:
            await callback.message.bot.send_message(row["telegram_id"], text, reply_markup=keyboard)
            sent += 1
        except Exception:
            continue

    summary = f"Запрос готовности отправлен {sent} пользователям."
    if skipped_confirmed:
        summary += f" Пропущено уже подтвердивших: {skipped_confirmed}."

    await callback.message.answer(summary)


@router.callback_query(F.data.startswith("admin_slot_broadcast:"))
async def admin_slot_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    _, template_id_str, booking_date = callback.data.split(":", 2)
    template_id = int(template_id_str)

    await state.update_data(slot_template_id=template_id, slot_booking_date=booking_date)

    await callback.message.answer(
        "Пришлите текст рассылки для пользователей, записанных на этот слот.\n"
        "Сообщение получат только те, кто записан на выбранную тренировку.\n\n"
        "Чтобы отменить и вернуться в меню, отправьте «Отмена» или /cancel."
    )
    await state.set_state(BroadcastSlot.text)


@router.message(BroadcastSlot.text)
async def admin_slot_broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    data = await state.get_data()
    template_id = data.get("slot_template_id")
    booking_date = data.get("slot_booking_date")

    text = message.text.strip()
    if not text:
        await message.answer("Текст сообщения не может быть пустым. Попробуйте ещё раз.", reply_markup=admin_menu)
        await state.clear()
        return

    if template_id is None or booking_date is None:
        await message.answer("Не удалось определить выбранный слот.", reply_markup=admin_menu)
        await state.clear()
        return

    telegram_ids = get_client_telegram_ids_for_slot(template_id, booking_date)
    if not telegram_ids:
        await message.answer("На этот слот нет ни одной записи для рассылки.", reply_markup=admin_menu)
        await state.clear()
        return

    await message.answer(f"Начинаю рассылку по {len(telegram_ids)} пользователям, записанным на выбранный слот...")

    success = 0
    failed = 0

    for chat_id in telegram_ids:
        try:
            await message.bot.send_message(chat_id, text)
            success += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(
        f"Рассылка по слоту завершена.\n"
        f"✅ Успешно: {success}\n"
        f"⚠️ Ошибок: {failed}",
        reply_markup=admin_menu,
    )


@router.message(F.text == "👥 Пользователи")
async def admin_users_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    clients = get_all_clients()
    if not clients:
        await message.answer("Пользователей пока нет.")
        return

    max_to_show = 50
    await message.answer(
        f"Список пользователей (показаны первые {min(len(clients), max_to_show)} из {len(clients)}):"
    )

    for idx, client in enumerate(clients[:max_to_show], start=1):
        phone = client["phone"] or "—"
        name = client["full_name"] or "—"
        created_at = client["created_at"] or ""
        is_admin_flag = client["is_admin"] == 1
        status = "👑 Админ" if is_admin_flag else "Обычный пользователь"

        text = (
            f"{idx}. {name}\n"
            f"📱 {phone}\n"
            f"🆔 {client['telegram_id']}\n"
            f"🕒 {created_at}\n"
            f"Статус: {status}"
        )

        # Управлять правами может только суперадмин из ADMIN_IDS
        if message.from_user.id in ADMIN_IDS:
            if is_admin_flag:
                button = InlineKeyboardButton(
                    text="❌ Снять админку",
                    callback_data=f"client_admin_off:{client['id']}",
                )
            else:
                button = InlineKeyboardButton(
                    text="👑 Сделать админом",
                    callback_data=f"client_admin_on:{client['id']}",
                )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
            await message.answer(text, reply_markup=keyboard)
        else:
            await message.answer(text)


@router.callback_query(F.data.startswith("client_admin_on:"))
async def client_admin_on(callback: CallbackQuery):
    # Только суперадмины из ADMIN_IDS могут выдавать админку
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    await callback.answer()
    client_id = int(callback.data.split(":", 1)[1])
    set_client_admin(client_id, True)
    await callback.message.edit_text("Пользователь назначен администратором.")


@router.callback_query(F.data.startswith("client_admin_off:"))
async def client_admin_off(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    await callback.answer()
    client_id = int(callback.data.split(":", 1)[1])
    set_client_admin(client_id, False)
    await callback.message.edit_text("Права администратора сняты с пользователя.")


@router.message(F.text == "👑 Администраторы")
async def admin_list_admins(message: Message):
    # Только суперадмин
    if message.from_user.id not in ADMIN_IDS:
        return

    admins = get_admin_clients()
    if not admins:
        await message.answer("Пока нет администраторов, кроме суперадмина.")
        return

    for client in admins:
        phone = client["phone"] or "—"
        name = client["full_name"] or "—"
        created_at = client["created_at"] or ""

        text = (
            f"{name}\n"
            f"📱 {phone}\n"
            f"🆔 {client['telegram_id']}\n"
            f"🕒 {created_at}"
        )

        button = InlineKeyboardButton(
            text="❌ Снять админку",
            callback_data=f"client_admin_off:{client['id']}",
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
        await message.answer(text, reply_markup=keyboard)


@router.message(F.text == "📢 Рассылка")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "Пришлите текст рассылки одним сообщением.\n"
        "Он будет отправлен всем пользователям бота.\n\n"
        "Чтобы отменить и вернуться в меню, отправьте «Отмена» или /cancel."
    )
    await state.set_state(Broadcast.text)


@router.message(Broadcast.text)
async def broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    text = message.text.strip()
    if not text:
        await message.answer("Текст сообщения не может быть пустым. Попробуйте ещё раз.", reply_markup=admin_menu)
        await state.clear()
        return

    telegram_ids = get_all_client_telegram_ids()
    if not telegram_ids:
        await message.answer("Нет пользователей для рассылки.", reply_markup=admin_menu)
        await state.clear()
        return

    await message.answer(f"Начинаю рассылку по {len(telegram_ids)} пользователям...")

    success = 0
    failed = 0

    for chat_id in telegram_ids:
        try:
            await message.bot.send_message(chat_id, text)
            success += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(
        f"Рассылка завершена.\n"
        f"✅ Успешно: {success}\n"
        f"⚠️ Ошибок: {failed}",
        reply_markup=admin_menu,
    )


@router.message(F.text == "📊 Статистика")
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return

    total_clients = get_clients_count()
    total_bookings = get_total_bookings()
    confirmed_bookings = get_total_confirmed_bookings()
    bookings_last_30 = get_bookings_last_days(30)

    text = (
        "📊 Статистика бота:\n\n"
        f"👥 Пользователей: {total_clients}\n"
        f"📅 Всего записей: {total_bookings}\n"
        f"✅ Подтверждённых записей: {confirmed_bookings}\n"
        f"📆 Записей за последние 30 дней: {bookings_last_30}"
    )

    await message.answer(text)


@router.message(F.text == "⬅️ Выйти из админки")
async def exit_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Вы вышли из админки.", reply_markup=main_menu)
