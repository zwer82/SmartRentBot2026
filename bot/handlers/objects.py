"""
Admin handlers for rental object CRUD (create, read, update, delete)
with photo upload support.
"""
import os
import logging

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from bot.config import ADMIN_IDS, PHOTOS_DIR
from bot.states import AddObject, EditObject
from bot.keyboards import (
    admin_objects_keyboard,
    admin_edit_objects_list_keyboard,
    admin_edit_single_object_keyboard,
    object_status_keyboard,
    confirm_delete_keyboard,
    back_to_menu_keyboard,
)
from bot.google_sheets import (
    get_all_objects,
    get_object,
    create_object,
    update_object_field,
    delete_object,
    OBJ_STATUS_MAP,
    OBJ_STATUS_REVERSE,
)
from bot.utils import download_photo

logger = logging.getLogger(__name__)


def register_object_handlers(dp: Dispatcher):
    # Navigation
    dp.register_callback_query_handler(
        admin_add_object_start, Text(equals="admin_add_object"), state="*"
    )
    dp.register_callback_query_handler(
        admin_edit_objects_list, Text(equals="admin_edit_objects_list"), state="*"
    )
    dp.register_callback_query_handler(
        admin_edit_object_menu, Text(startswith="admin_edit_object:"), state="*"
    )
    dp.register_callback_query_handler(
        admin_edit_field, Text(startswith="edit_field:"), state="*"
    )
    dp.register_callback_query_handler(
        admin_obj_set_status, Text(startswith="obj_set_status:"), state="*"
    )
    dp.register_callback_query_handler(
        admin_delete_object_confirm, Text(startswith="delete_obj:"), state="*"
    )
    dp.register_callback_query_handler(
        admin_confirm_delete, Text(startswith="confirm_delete:"), state="*"
    )

    # FSM: AddObject
    dp.register_message_handler(add_object_name, state=AddObject.name)
    dp.register_message_handler(add_object_price, state=AddObject.price)
    dp.register_message_handler(add_object_description, state=AddObject.description)
    dp.register_message_handler(add_object_photo, state=AddObject.photo, content_types=["photo"])
    dp.register_callback_query_handler(
        add_object_confirm, Text(equals="obj_create_ok"), state=AddObject.confirm
    )
    dp.register_callback_query_handler(
        add_object_retry_photo, Text(equals="obj_create_retry_photo"), state=AddObject.confirm
    )

    # FSM: EditObject
    dp.register_message_handler(edit_object_value, state=EditObject.value)


# ─── Guard ──────────────────────────────────────────────────
def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _require_admin(call_or_msg) -> bool:
    uid = call_or_msg.from_user.id
    if not _is_admin(uid):
        if hasattr(call_or_msg, "answer"):
            await call_or_msg.answer("⛔ Доступ только для администраторов.", show_alert=True)
        return False
    return True


# ═══════════════════  ADD OBJECT  ═══════════════════════════

async def admin_add_object_start(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
    await AddObject.name.set()
    await call.message.edit_text(
        "➕ *Добавление нового объекта*\n\n"
        "Шаг 1 из 4 — введите *название* объекта:\n"
        "Например: «Двухкомнатная квартира на Ленина»",
        parse_mode="Markdown",
    )
    await call.answer()


async def add_object_name(message: types.Message, state: FSMContext):
    if len(message.text.strip()) < 3:
        await message.answer("Название должно быть минимум 3 символа.")
        return
    async with state.proxy() as data:
        data["name"] = message.text.strip()
    await AddObject.next()
    await message.answer(
        "💰 *Шаг 2 из 4* — введите *цену* в рублях за месяц:\n"
        "Например: `25000`",
        parse_mode="Markdown",
    )


async def add_object_price(message: types.Message, state: FSMContext):
    price = message.text.strip()
    if not price.isdigit():
        await message.answer("Пожалуйста, введите число (только цифры).")
        return
    async with state.proxy() as data:
        data["price"] = price
    await AddObject.next()
    await message.answer(
        "📝 *Шаг 3 из 4* — напишите *описание* объекта:\n"
        "Этаж, ремонт, мебель, удобства — всё, что важно.",
        parse_mode="Markdown",
    )


async def add_object_description(message: types.Message, state: FSMContext):
    if len(message.text.strip()) < 10:
        await message.answer("Описание должно быть минимум 10 символов.")
        return
    async with state.proxy() as data:
        data["description"] = message.text.strip()
    await AddObject.next()
    await message.answer(
        "🖼 *Шаг 4 из 4* — отправьте *фото* объекта.\n"
        "_(можно пропустить, отправив /skip)_",
        parse_mode="Markdown",
    )


async def add_object_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file_id = photo.file_id

    # Показываем превью
    async with state.proxy() as data:
        data["photo_file_id"] = file_id

    preview_text = (
        "🖼 *Фото получено!*\n\n"
        "Проверьте и подтвердите создание объекта."
    )

    from bot.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Создать объект", callback_data="obj_create_ok"),
        InlineKeyboardButton("🔄 Заменить фото", callback_data="obj_create_retry_photo"),
    )

    await message.reply_photo(photo.file_id, caption=preview_text, parse_mode="Markdown", reply_markup=kb)
    await AddObject.confirm.set()


async def add_object_confirm(call: types.CallbackQuery, state: FSMContext):
    if not await _require_admin(call):
        return
    data = await state.get_data()

    obj_data = {
        "name": data["name"],
        "price": data["price"],
        "description": data["description"],
        "photo_file_id": data.get("photo_file_id", ""),
        "photo_local_path": "",
        "status": "available",
    }

    obj_id = create_object(obj_data)
    if obj_id is None:
        await call.message.edit_text("❌ Ошибка при создании объекта.")
        await state.finish()
        await call.answer()
        return

    # Опционально скачиваем фото
    if obj_data["photo_file_id"]:
        path = download_photo(call.bot, obj_data["photo_file_id"], PHOTOS_DIR, obj_id)
        if path:
            update_object_field(obj_id, "photo_local_path", path)

    await state.finish()
    await call.message.edit_text(
        f"✅ *Объект создан!*\n\n"
        f"ID: *#{obj_id}*\n"
        f"Название: *{data['name']}*\n"
        f"Цена: {data['price']} ₽/мес\n"
        f"Статус: {OBJ_STATUS_MAP['available']}",
        parse_mode="Markdown",
        reply_markup=admin_objects_keyboard(),
    )
    await call.answer()


async def add_object_retry_photo(call: types.CallbackQuery, state: FSMContext):
    if not await _require_admin(call):
        return
    await AddObject.photo.set()
    await call.message.edit_text(
        "🖼 Отправьте новое фото объекта:",
    )
    await call.answer()


# ═══════════════════  EDIT / DELETE  ════════════════════════

async def admin_edit_objects_list(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
    objects = get_all_objects()
    if not objects:
        await call.message.edit_text(
            "❌ Нет объектов для редактирования.",
            reply_markup=admin_objects_keyboard(),
        )
        await call.answer()
        return

    await call.message.edit_text(
        "🗂 *Список объектов*\n\nВыберите объект для редактирования:",
        parse_mode="Markdown",
        reply_markup=admin_edit_objects_list_keyboard(objects),
    )
    await call.answer()


async def admin_edit_object_menu(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
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
        f"🖼 *Фото:* {'✅ есть' if obj.get('photo_file_id') else '❌ нет'}\n\n"
        "Выберите, что изменить:"
    )
    await call.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_edit_single_object_keyboard(obj_id),
    )
    await call.answer()


async def admin_edit_field(call: types.CallbackQuery, state: FSMContext):
    if not await _require_admin(call):
        return
    _, obj_id_str, field = call.data.split(":")
    obj_id = int(obj_id_str)

    if field == "status":
        obj = get_object(obj_id)
        await call.message.edit_text(
            f"📌 Выберите новый статус для *{obj['name']}*:",
            parse_mode="Markdown",
            reply_markup=object_status_keyboard(obj_id),
        )
        await call.answer()
        return

    if field == "photo":
        await EditObject.field.set()
        async with state.proxy() as data:
            data["obj_id"] = obj_id
            data["field"] = "photo_file_id"
        await call.message.edit_text("🖼 Отправьте новое фото:")
        await call.answer()
        return

    field_names = {"name": "название", "price": "цену", "description": "описание"}
    await EditObject.field.set()
    async with state.proxy() as data:
        data["obj_id"] = obj_id
        data["field"] = field
    await call.message.edit_text(
        f"✏️ Введите новое *{field_names.get(field, field)}*:",
        parse_mode="Markdown",
    )
    await call.answer()


async def edit_object_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    obj_id = data["obj_id"]
    field = data["field"]
    value = message.text.strip()

    if field == "price" and not value.isdigit():
        await message.answer("Цена должна быть числом.")
        return
    if field == "name" and len(value) < 3:
        await message.answer("Название должно быть минимум 3 символа.")
        return
    if field == "description" and len(value) < 10:
        await message.answer("Описание должно быть минимум 10 символов.")
        return

    success = update_object_field(obj_id, field, value)
    await state.finish()

    if not success:
        await message.answer("❌ Ошибка обновления.")
        return

    obj = get_object(obj_id)
    obj_name = obj["name"] if obj else f"#{obj_id}"
    await message.answer(
        f"✅ *{obj_name}* — поле «{field}» обновлено!",
        parse_mode="Markdown",
        reply_markup=admin_edit_single_object_keyboard(obj_id),
    )


async def admin_obj_set_status(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
    _, obj_id_str, status = call.data.split(":")
    obj_id = int(obj_id_str)

    success = update_object_field(obj_id, "status", status)
    if not success:
        await call.answer("❌ Ошибка обновления статуса.", show_alert=True)
        return

    status_text = OBJ_STATUS_MAP.get(status, status)
    await call.message.edit_text(
        f"✅ Статус объекта *#{obj_id}* → {status_text}",
        parse_mode="Markdown",
        reply_markup=admin_edit_single_object_keyboard(obj_id),
    )
    await call.answer()


async def admin_delete_object_confirm(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
    obj_id = int(call.data.split(":")[1])
    obj = get_object(obj_id)
    name = obj["name"] if obj else f"#{obj_id}"

    await call.message.edit_text(
        f"🗑 *Удалить объект*\n\n"
        f"Вы уверены, что хотите удалить «{name}»?\n"
        "Это действие необратимо.",
        parse_mode="Markdown",
        reply_markup=confirm_delete_keyboard(obj_id),
    )
    await call.answer()


async def admin_confirm_delete(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
    obj_id = int(call.data.split(":")[1])
    success = delete_object(obj_id)

    if success:
        await call.message.edit_text(
            f"✅ Объект *#{obj_id}* удалён.",
            parse_mode="Markdown",
            reply_markup=admin_objects_keyboard(),
        )
    else:
        await call.message.edit_text(
            "❌ Ошибка удаления.",
            reply_markup=admin_objects_keyboard(),
        )
    await call.answer()
