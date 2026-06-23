from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ────────────────────────  User  ────────────────────────────

def main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🏠 Доступные объекты", callback_data="objects_list"),
        InlineKeyboardButton("📋 Мои заявки", callback_data="my_applications"),
        InlineKeyboardButton("👤 Мой профиль", callback_data="profile"),
    )
    if is_admin:
        kb.add(InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_panel"))
    return kb


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return kb


# ────────────────────  Objects list  ────────────────────────

def objects_list_keyboard(objects: list, page: int = 0) -> InlineKeyboardMarkup:
    """Список объектов с пагинацией."""
    kb = InlineKeyboardMarkup(row_width=1)
    for obj in objects:
        label = f"{obj['name']} — {obj['price']} ₽/мес"
        if obj.get("status"):
            kb.add(InlineKeyboardButton(label, callback_data=f"view_object:{obj['id']}"))
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"objects_page:{page - 1}"))
    nav_row.append(InlineKeyboardButton("🏠 Меню", callback_data="main_menu"))
    if len(objects) == 10:  # полная страница — есть следующая
        nav_row.append(InlineKeyboardButton("➡️ Вперёд", callback_data=f"objects_page:{page + 1}"))
    kb.row(*nav_row)
    return kb


def object_card_keyboard(obj_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для карточки объекта."""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📩 Подать заявку", callback_data=f"apply:{obj_id}"))
    if is_admin:
        kb.add(InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_obj:{obj_id}"))
        kb.add(InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_obj:{obj_id}"))
    kb.add(InlineKeyboardButton("⬅️ Назад к списку", callback_data="objects_list"))
    return kb


# ────────────────────  Registration  ────────────────────────

def registration_confirm_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data="reg_confirm"),
        InlineKeyboardButton("🔄 Заново", callback_data="reg_restart"),
    )
    return kb


# ────────────────────  User applications  ───────────────────

def applications_list_keyboard(apps: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for app in apps:
        label = f"#{app['id']} — {app['status']}"
        kb.add(InlineKeyboardButton(label, callback_data=f"view_application:{app['id']}"))
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return kb


# ────────────────────────  Admin  ───────────────────────────

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🏘 Управление объектами", callback_data="admin_objects"),
        InlineKeyboardButton("📋 Заявки", callback_data="admin_applications"),
        InlineKeyboardButton("📢 Уведомить всех", callback_data="admin_broadcast"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
    )
    return kb


def admin_objects_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ Добавить объект", callback_data="admin_add_object"),
        InlineKeyboardButton("📋 Список объектов", callback_data="admin_edit_objects_list"),
        InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel"),
    )
    return kb


def admin_applications_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🆕 Новые", callback_data="admin_apps_filter:new"),
        InlineKeyboardButton("🟡 В обработке", callback_data="admin_apps_filter:processing"),
        InlineKeyboardButton("🟢 Подтверждён", callback_data="admin_apps_filter:confirmed"),
        InlineKeyboardButton("🔵 Завершён", callback_data="admin_apps_filter:completed"),
        InlineKeyboardButton("🔴 Отменён", callback_data="admin_apps_filter:cancelled"),
        InlineKeyboardButton("📋 Все заявки", callback_data="admin_apps_filter:all"),
        InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel"),
    )
    return kb


def admin_status_change_keyboard(app_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🟡 В обработке", callback_data=f"app_set_status:{app_id}:processing"),
        InlineKeyboardButton("🟢 Подтверждён", callback_data=f"app_set_status:{app_id}:confirmed"),
        InlineKeyboardButton("🔵 Завершён", callback_data=f"app_set_status:{app_id}:completed"),
        InlineKeyboardButton("🔴 Отменён", callback_data=f"app_set_status:{app_id}:cancelled"),
    )
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="admin_applications"))
    return kb


def admin_edit_objects_list_keyboard(objects: list) -> InlineKeyboardMarkup:
    """Список объектов для админа (управление)."""
    kb = InlineKeyboardMarkup(row_width=1)
    for obj in objects:
        kb.add(InlineKeyboardButton(
            f"{obj['name']} — {obj['price']} ₽",
            callback_data=f"admin_edit_object:{obj['id']}",
        ))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="admin_objects"))
    return kb


def admin_edit_single_object_keyboard(obj_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("✏️ Название", callback_data=f"edit_field:{obj_id}:name"),
        InlineKeyboardButton("💰 Цена", callback_data=f"edit_field:{obj_id}:price"),
        InlineKeyboardButton("📝 Описание", callback_data=f"edit_field:{obj_id}:description"),
        InlineKeyboardButton("🖼 Фото", callback_data=f"edit_field:{obj_id}:photo"),
        InlineKeyboardButton("📌 Статус", callback_data=f"edit_field:{obj_id}:status"),
        InlineKeyboardButton("🗑 Удалить объект", callback_data=f"delete_obj:{obj_id}"),
        InlineKeyboardButton("⬅️ Назад", callback_data="admin_edit_objects_list"),
    )
    return kb


def object_status_keyboard(obj_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🟢 Доступен", callback_data=f"obj_set_status:{obj_id}:available"),
        InlineKeyboardButton("🔴 Занят", callback_data=f"obj_set_status:{obj_id}:rented"),
        InlineKeyboardButton("🟡 На обслуживании", callback_data=f"obj_set_status:{obj_id}:maintenance"),
        InlineKeyboardButton("⬅️ Назад", callback_data=f"admin_edit_object:{obj_id}"),
    )
    return kb


def confirm_delete_keyboard(obj_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete:{obj_id}"),
        InlineKeyboardButton("❌ Нет", callback_data=f"admin_edit_object:{obj_id}"),
    )
    return kb
