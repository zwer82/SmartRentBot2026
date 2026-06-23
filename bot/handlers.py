"""
User-facing handlers: main menu, objects list, registration, profile, applications.
Also registers admin and object handlers from submodules.
"""
import logging

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from bot.config import ADMIN_IDS
from bot.states import Registration
from bot.keyboards import (
    main_menu_keyboard,
    objects_list_keyboard,
    object_card_keyboard,
    registration_confirm_keyboard,
    applications_list_keyboard,
    back_to_menu_keyboard,
)
from bot.google_sheets import (
    get_all_objects,
    get_object,
    create_application,
    get_applications_by_user,
    get_all_applications,
    get_application,
    check_duplicate_user,
    check_duplicate_phone,
    APP_STATUS_MAP,
)

logger = logging.getLogger(__name__)

_OBJECTS_PER_PAGE = 10


def register_all_handlers(dp: Dispatcher):
    """Главная регистрация всех обработчиков."""
    # Импортируем и регистрируем подмодули
    from bot.handlers.admin import register_admin_handlers
    from bot.handlers.objects import register_object_handlers

    register_admin_handlers(dp)
    register_object_handlers(dp)

    # User handlers
    dp.register_message_handler(cmd_start, commands=["start"], state="*")
    dp.register_callback_query_handler(cmd_start, Text(equals="main_menu"), state="*")

    dp.register_callback_query_handler(show_objects_list, Text(equals="objects_list"), state="*")
    dp.register_callback_query_handler(
        show_objects_list, Text(startswith="objects_page:"), state="*"
    )
    dp.register_callback_query_handler(
        show_object_card, Text(startswith="view_object:"), state="*"
    )

    dp.register_callback_query_handler(start_application, Text(startswith="apply:"), state="*")
    dp.register_message_handler(process_name, state=Registration.name)
    dp.register_message_handler(process_phone, state=Registration.phone)
    dp.register_message_handler(process_city, state=Registration.city)
    dp.register_callback_query_handler(confirm_application, Text(equals="reg_confirm"), state="*")
    dp.register_callback_query_handler(restart_application, Text(equals="reg_restart"), state="*")

    dp.register_callback_query_handler(show_profile, Text(equals="profile"), state="*")
    dp.register_callback_query_handler(
        show_my_applications, Text(equals="my_applications"), state="*"
    )
    dp.register_callback_query_handler(
        show_application_detail, Text(startswith="view_application:"), state="*"
    )


# ── /start ──────────────────────────────────────────────────
async def cmd_start(update: types.Message | types.CallbackQuery, state: FSMContext = None):
    if state:
        await state.finish()

    user = update.from_user if isinstance(update, types.Message) else update.message.from_user
    is_admin = user.id in ADMIN_IDS
    text = (
        f"🏠 *SmartRentBot*\n\n"
        f"Привет, {user.first_name}! 👋\n"
        "Я помогу вам найти идеальную квартиру или дом для аренды.\n\n"
        "📌 *Доступные команды:*\n"
        "• Просматривайте объекты\n"
        "• Оставляйте заявки\n"
        "• Отслеживайте статус"
    )

    markup = main_menu_keyboard(is_admin=is_admin)
    if isinstance(update, types.Message):
        await update.answer(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.message.edit_text(text, parse_mode="Markdown", reply_markup=markup)


# ── Список объектов ─────────────────────────────────────────
async def show_objects_list(call: types.CallbackQuery):
    page = 0
    if call.data.startswith("objects_page:"):
        page = int(call.data.split(":")[1])

    all_objects = get_all_objects(status="available")
    start = page * _OBJECTS_PER_PAGE
    end = start + _OBJECTS_PER_PAGE
    page_objects = all_objects[start:end]

    if not page_objects:
        await call.message.edit_text(
            "😔 Пока нет доступных объектов.\nЗагляните позже!",
            reply_markup=back_to_menu_keyboard(),
        )
        await call.answer()
        return

    text = f"🏘 *Доступные объекты*\nСтраница {page + 1}\n\n"
    for i, obj in enumerate(page_objects, start=start + 1):
        text += f"{i}. *{obj['name']}* — {obj['price']} ₽/мес\n"

    await call.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=objects_list_keyboard(page_objects, page),
    )
    await call.answer()


async def show_object_card(call: types.CallbackQuery):
    obj_id = int(call.data.split(":")[1])
    obj = get_object(obj_id)
    if not obj:
        await call.answer("❌ Объект не найден.", show_alert=True)
        return

    text = (
        f"🏘 *{obj['name']}*\n\n"
        f"💰 *Цена:* {obj['price']} ₽/мес\n"
        f"📝 *Описание:* {obj['description']}\n"
        f"📌 *Статус:* {obj['status']}\n"
    )
    is_admin = call.from_user.id in ADMIN_IDS
    markup = object_card_keyboard(obj_id, is_admin=is_admin)

    if obj.get("photo_file_id"):
        await call.message.delete()
        await call.message.answer_photo(
            obj["photo_file_id"],
            caption=text,
            parse_mode="Markdown",
            reply_markup=markup,
        )
    else:
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    await call.answer()


# ── Подача заявки ───────────────────────────────────────────
async def start_application(call: types.CallbackQuery, state: FSMContext = None):
    obj_id = int(call.data.split(":")[1])

    # Дубликат по Telegram ID
    if check_duplicate_user(call.from_user.id):
        await call.message.edit_text(
            "❌ Вы уже оставляли заявку.\n"
            "Ожидайте ответа от менеджера или проверьте статус в разделе «Мои заявки».",
            reply_markup=back_to_menu_keyboard(),
        )
        await call.answer()
        return

    async with state.proxy() as data:
        data["object_id"] = obj_id

    await Registration.name.set()
    obj = get_object(obj_id)
    obj_name = obj["name"] if obj else "объект"

    await call.message.edit_text(
        f"📩 *Подача заявки*\n\n"
        f"Объект: *{obj_name}*\n\n"
        "Шаг 1 из 3 — введите ваше имя и фамилию:",
        parse_mode="Markdown",
    )
    await call.answer()


async def process_name(message: types.Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("Пожалуйста, введите корректное имя (минимум 2 символа).")
        return
    async with state.proxy() as data:
        data["name"] = message.text.strip()
    await Registration.next()
    await message.answer(
        "📞 *Шаг 2 из 3*\n\nВведите ваш номер телефона:\nПример: +7 (999) 123-45-67",
        parse_mode="Markdown",
    )


async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if len(phone) < 5:
        await message.answer("Пожалуйста, введите корректный номер телефона.")
        return

    # Дубликат по телефону
    if check_duplicate_phone(phone):
        await message.answer(
            "❌ Пользователь с таким номером телефона уже оставлял заявку.\n"
            "Если это вы — ожидайте ответа менеджера.",
            reply_markup=back_to_menu_keyboard(),
        )
        await state.finish()
        return

    async with state.proxy() as data:
        data["phone"] = phone
    await Registration.next()
    await message.answer(
        "🏙 *Шаг 3 из 3*\n\nВ каком городе вы ищете жильё?",
        parse_mode="Markdown",
    )


async def process_city(message: types.Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("Пожалуйста, введите название города.")
        return
    async with state.proxy() as data:
        data["city"] = message.text.strip()

    data = await state.get_data()
    obj = get_object(data["object_id"])
    obj_name = obj["name"] if obj else "объект"

    summary = (
        "📋 *Проверьте данные:*\n\n"
        f"🏘 Объект: *{obj_name}*\n"
        f"👤 Имя: *{data['name']}*\n"
        f"📞 Телефон: *{data['phone']}*\n"
        f"🏙 Город: *{data['city']}*\n\n"
        "Всё верно?"
    )
    await message.answer(summary, parse_mode="Markdown", reply_markup=registration_confirm_keyboard())


async def confirm_application(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    app_data = {
        "telegram_id": call.from_user.id,
        "name": data["name"],
        "phone": data["phone"],
        "city": data["city"],
        "object_id": data.get("object_id", ""),
    }

    app_id = create_application(app_data)
    if app_id is None:
        await call.message.edit_text(
            "❌ Произошла ошибка при создании заявки. Попробуйте позже.",
            reply_markup=back_to_menu_keyboard(),
        )
        await call.answer()
        await state.finish()
        return

    await state.finish()

    await call.message.edit_text(
        "✅ *Заявка создана!*\n\n"
        f"Номер заявки: *#{app_id}*\n"
        f"Статус: {APP_STATUS_MAP['new']}\n\n"
        "Наш менеджер свяжется с вами в ближайшее время.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(is_admin=call.from_user.id in ADMIN_IDS),
    )
    await call.answer()

    # Уведомление админам
    await _notify_admins_new_application(call.bot, app_id, data)


async def restart_application(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.finish()
    # Возвращаем к шагу 1 с сохранённым object_id
    await Registration.name.set()
    async with state.proxy() as d:
        d["object_id"] = data.get("object_id")
    obj = get_object(data.get("object_id", 0))
    obj_name = obj["name"] if obj else "объект"
    await call.message.edit_text(
        f"📩 *Подача заявки*\n\n"
        f"Объект: *{obj_name}*\n\n"
        "Шаг 1 из 3 — введите ваше имя и фамилию:",
        parse_mode="Markdown",
    )
    await call.answer()


# ── Профиль ─────────────────────────────────────────────────
async def show_profile(call: types.CallbackQuery):
    apps = get_applications_by_user(call.from_user.id)
    if not apps:
        await call.message.edit_text(
            "👤 *Мой профиль*\n\n"
            "У вас пока нет активных заявок.\n"
            "Перейдите в «Доступные объекты», чтобы оставить заявку.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(is_admin=call.from_user.id in ADMIN_IDS),
        )
        await call.answer()
        return

    last = apps[-1]
    text = (
        "👤 *Мой профиль*\n\n"
        f"**Имя:** {last['name']}\n"
        f"**Телефон:** {last['phone']}\n"
        f"**Город:** {last['city']}\n"
        f"**Всего заявок:** {len(apps)}\n"
        f"**Последняя заявка:** #{last['id']} — {last['status']}"
    )
    await call.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(is_admin=call.from_user.id in ADMIN_IDS),
    )
    await call.answer()


# ── Мои заявки ──────────────────────────────────────────────
async def show_my_applications(call: types.CallbackQuery):
    apps = get_applications_by_user(call.from_user.id)
    if not apps:
        await call.message.edit_text(
            "📋 У вас пока нет заявок.",
            reply_markup=main_menu_keyboard(is_admin=call.from_user.id in ADMIN_IDS),
        )
        await call.answer()
        return

    text = "📋 *Мои заявки*\n\n"
    for app in apps[-10:]:  # последние 10
        text += f"• *#{app['id']}* — {app['status']}\n"

    await call.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=applications_list_keyboard(apps[-10:]),
    )
    await call.answer()


async def show_application_detail(call: types.CallbackQuery):
    app_id = int(call.data.split(":")[1])
    app = get_application(app_id)
    if not app:
        await call.answer("❌ Заявка не найдена.", show_alert=True)
        return

    # Проверка принадлежности
    if str(app["telegram_id"]) != str(call.from_user.id) and call.from_user.id not in ADMIN_IDS:
        await call.answer("⛔ Это не ваша заявка.", show_alert=True)
        return

    text = (
        f"📋 *Заявка #{app['id']}*\n\n"
        f"👤 **Имя:** {app['name']}\n"
        f"📞 **Телефон:** {app['phone']}\n"
        f"🏙 **Город:** {app['city']}\n"
        f"🏘 **Объект:** {app.get('object_id', '—')}\n"
        f"📌 **Статус:** {app['status']}\n"
        f"🕐 **Создана:** {app['created_at']}\n"
        f"🕐 **Обновлена:** {app.get('updated_at', '—')}"
    )

    await call.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer()


# ── Уведомления ─────────────────────────────────────────────
async def _notify_admins_new_application(bot, app_id: int, data: dict):
    from bot.config import ADMIN_IDS as ADMINS

    text = (
        "🆕 *Новая заявка!*\n\n"
        f"**Номер:** #{app_id}\n"
        f"**Имя:** {data['name']}\n"
        f"**Телефон:** {data['phone']}\n"
        f"**Город:** {data['city']}\n"
        f"**Объект ID:** {data.get('object_id', '—')}"
    )
    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, text, parse_mode="Markdown")
        except Exception as exc:
            logger.warning("Cannot notify admin %s: %s", admin_id, exc)
