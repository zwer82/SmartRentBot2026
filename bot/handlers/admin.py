"""
Admin panel handlers: manage applications, broadcast, access control.
"""
import logging

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text

from bot.config import ADMIN_IDS
from bot.keyboards import (
    admin_panel_keyboard,
    admin_applications_keyboard,
    admin_status_change_keyboard,
    back_to_menu_keyboard,
    main_menu_keyboard,
)
from bot.google_sheets import (
    get_all_applications,
    get_application,
    update_application_status,
    APP_STATUS_MAP,
)

logger = logging.getLogger(__name__)


def register_admin_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(admin_panel, Text(equals="admin_panel"), state="*")
    dp.register_callback_query_handler(admin_objects, Text(equals="admin_objects"), state="*")
    dp.register_callback_query_handler(
        admin_applications, Text(equals="admin_applications"), state="*"
    )
    dp.register_callback_query_handler(
        admin_apps_filter, Text(startswith="admin_apps_filter:"), state="*"
    )
    dp.register_callback_query_handler(
        admin_view_application, Text(startswith="admin_view_app:"), state="*"
    )
    dp.register_callback_query_handler(
        admin_set_status, Text(startswith="app_set_status:"), state="*"
    )
    dp.register_callback_query_handler(
        admin_broadcast_start, Text(equals="admin_broadcast"), state="*"
    )
    dp.register_message_handler(admin_broadcast_send, state="*")


# ── Проверка админа ────────────────────────────────────────
def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _require_admin(call: types.CallbackQuery) -> bool:
    if not _is_admin(call.from_user.id):
        await call.answer("⛔ Доступ только для администраторов.", show_alert=True)
        return False
    return True


# ── Админ-панель ────────────────────────────────────────────
async def admin_panel(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
    await call.message.edit_text(
        "⚙️ *Админ-панель*\n\nВыберите раздел:",
        parse_mode="Markdown",
        reply_markup=admin_panel_keyboard(),
    )
    await call.answer()


# ── Управление объектами (перенаправление) ──────────────────
async def admin_objects(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
    # Импортируем клавиатуру из objects
    from bot.keyboards import admin_objects_keyboard
    await call.message.edit_text(
        "🏘 *Управление объектами*\n\n"
        "Добавьте новый объект или отредактируйте существующий.",
        parse_mode="Markdown",
        reply_markup=admin_objects_keyboard(),
    )
    await call.answer()


# ── Заявки ──────────────────────────────────────────────────
async def admin_applications(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
    await call.message.edit_text(
        "📋 *Заявки*\n\nВыберите фильтр по статусу:",
        parse_mode="Markdown",
        reply_markup=admin_applications_keyboard(),
    )
    await call.answer()


async def admin_apps_filter(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
    status = call.data.split(":")[1]
    apps = get_all_applications(status=None if status == "all" else status)

    if not apps:
        await call.message.edit_text(
            "❌ Нет заявок с таким статусом.",
            reply_markup=admin_applications_keyboard(),
        )
        await call.answer()
        return

    text = f"📋 *Заявки* ({len(apps)})\n\n"
    for app in apps[-20:]:  # последние 20
        text += f"• *#{app['id']}* — {app['name']} — {app['status']}\n"

    from bot.keyboards import admin_applications_keyboard
    await call.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_applications_keyboard(),
    )
    await call.answer()


# ── Просмотр заявки админом ─────────────────────────────────
async def admin_view_application(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
    app_id = int(call.data.split(":")[1])
    app = get_application(app_id)
    if not app:
        await call.answer("❌ Заявка не найдена.", show_alert=True)
        return

    text = (
        f"📋 *Заявка #{app['id']}*\n\n"
        f"👤 **Имя:** {app['name']}\n"
        f"📞 **Телефон:** {app['phone']}\n"
        f"🏙 **Город:** {app['city']}\n"
        f"🏘 **Объект ID:** {app.get('object_id', '—')}\n"
        f"🆔 **Telegram ID:** `{app['telegram_id']}`\n"
        f"📌 **Статус:** {app['status']}\n"
        f"🕐 **Создана:** {app['created_at']}\n"
        f"🕐 **Обновлена:** {app.get('updated_at', '—')}"
    )
    await call.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_status_change_keyboard(app_id),
    )
    await call.answer()


# ── Смена статуса заявки ───────────────────────────────────
async def admin_set_status(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
    parts = call.data.split(":")
    app_id = int(parts[1])
    new_status = parts[2]

    app = get_application(app_id)
    if not app:
        await call.answer("❌ Заявка не найдена.", show_alert=True)
        return

    success = update_application_status(app_id, new_status)
    if not success:
        await call.answer("❌ Ошибка обновления.", show_alert=True)
        return

    status_text = APP_STATUS_MAP.get(new_status, new_status)

    await call.message.edit_text(
        f"✅ Статус заявки *#{app_id}* обновлён → {status_text}",
        parse_mode="Markdown",
        reply_markup=admin_applications_keyboard(),
    )

    # Уведомление пользователю
    try:
        await call.bot.send_message(
            app["telegram_id"],
            f"🔔 *Статус вашей заявки изменился!*\n\n"
            f"Заявка *#{app_id}*\n"
            f"Новый статус: {status_text}",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.warning("Cannot notify user %s: %s", app["telegram_id"], exc)

    await call.answer("✅ Статус обновлён!")


# ── Рассылка ────────────────────────────────────────────────
async def admin_broadcast_start(call: types.CallbackQuery):
    if not await _require_admin(call):
        return
    await call.message.edit_text(
        "📢 *Рассылка*\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям.\n"
        "_(можно с фото или просто текст)_\n\n"
        "Для отмены нажмите кнопку ниже.",
        parse_mode="Markdown",
        reply_markup=back_to_menu_keyboard(),
    )
    # Сохраняем флаг в памяти (глобально)
    call.bot["broadcast_active"] = True
    await call.answer()


async def admin_broadcast_send(message: types.Message):
    """Перехватывает следующее сообщение от админа для рассылки."""
    if not _is_admin(message.from_user.id):
        return
    if not message.bot.get("broadcast_active"):
        return

    # Получаем список всех заявок, собираем уникальные Telegram ID
    apps = get_all_applications()
    user_ids = set()
    for app in apps:
        try:
            user_ids.add(int(app["telegram_id"]))
        except (ValueError, TypeError):
            continue

    if not user_ids:
        await message.answer("❌ Нет пользователей для рассылки.")
        message.bot["broadcast_active"] = False
        return

    sent = 0
    failed = 0
    caption = "📢 *Сообщение от администрации*\n\n" + (message.text or message.caption or "")
    for uid in user_ids:
        try:
            if message.photo:
                await message.bot.send_photo(uid, message.photo[-1].file_id, caption=caption)
            elif message.text:
                await message.bot.send_message(uid, caption, parse_mode="Markdown")
            sent += 1
        except Exception:
            failed += 1

    message.bot["broadcast_active"] = False
    await message.answer(
        f"✅ *Рассылка завершена*\n\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}",
        parse_mode="Markdown",
    )
