import logging
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread import Worksheet

from bot.config import (
    GOOGLE_SHEETS_CREDENTIALS_FILE,
    GOOGLE_SHEET_ID,
    APPLICATIONS_SHEET_NAME,
    OBJECTS_SHEET_NAME,
)

logger = logging.getLogger(__name__)

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# ── Статусы ─────────────────────────────────────────────────
APP_STATUS_MAP = {
    "new": "🆕 Новый",
    "processing": "🟡 В обработке",
    "confirmed": "🟢 Подтверждён",
    "completed": "🔵 Завершён",
    "cancelled": "🔴 Отменён",
}
APP_STATUS_REVERSE = {v: k for k, v in APP_STATUS_MAP.items()}

OBJ_STATUS_MAP = {
    "available": "🟢 Доступен",
    "rented": "🔴 Занят",
    "maintenance": "🟡 На обслуживании",
}
OBJ_STATUS_REVERSE = {v: k for k, v in OBJ_STATUS_MAP.items()}


# ── Client ──────────────────────────────────────────────────
def _get_client():
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        GOOGLE_SHEETS_CREDENTIALS_FILE, SCOPE
    )
    return gspread.authorize(creds)


def _get_ws(sheet_name: str) -> Worksheet:
    client = _get_client()
    sheet = client.open_by_key(GOOGLE_SHEET_ID)
    return sheet.worksheet(sheet_name)


def _ensure_headers(ws, headers: list):
    if not ws.get_all_values():
        ws.append_row(headers)


# ═══════════════════  APPLICATIONS  ═════════════════════════

APP_HEADERS = [
    "ID заявки", "Telegram ID", "Имя", "Телефон", "Город",
    "Объект (ID)", "Статус", "Дата создания", "Обновлено",
]

_next_app_id = 0


def _get_next_app_id(ws: Worksheet) -> int:
    global _next_app_id
    if _next_app_id == 0:
        values = ws.col_values(1)[1:]  # без заголовка
        ids = [int(v) for v in values if v.isdigit()]
        _next_app_id = max(ids) + 1 if ids else 1
    else:
        _next_app_id += 1
    return _next_app_id


def create_application(data: dict) -> int | None:
    """Создать заявку. Возвращает ID заявки или None."""
    try:
        ws = _get_ws(APPLICATIONS_SHEET_NAME)
        _ensure_headers(ws, APP_HEADERS)
    except Exception as exc:
        logger.error("Cannot open applications sheet: %s", exc)
        return None

    app_id = _get_next_app_id(ws)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([
        app_id,
        data["telegram_id"],
        data["name"],
        data["phone"],
        data["city"],
        data.get("object_id", ""),
        APP_STATUS_MAP["new"],
        now,
        now,
    ])
    logger.info("Application #%s created for tg_id %s", app_id, data["telegram_id"])
    return app_id


def get_application(app_id: int) -> dict | None:
    """Получить одну заявку."""
    try:
        ws = _get_ws(APPLICATIONS_SHEET_NAME)
    except Exception:
        return None
    all_data = ws.get_all_values()
    for idx, row in enumerate(all_data[1:], start=2):
        if row and row[0].isdigit() and int(row[0]) == app_id:
            return _row_to_app(row)
    return None


def get_applications_by_user(tg_id: int) -> list:
    """Все заявки пользователя."""
    try:
        ws = _get_ws(APPLICATIONS_SHEET_NAME)
        _ensure_headers(ws, APP_HEADERS)
    except Exception:
        return []
    all_data = ws.get_all_values()
    result = []
    for row in all_data[1:]:
        if row and row[1] == str(tg_id):
            result.append(_row_to_app(row))
    return result


def get_all_applications(status: str | None = None) -> list:
    """Все заявки, опционально по статусу (ключ)."""
    try:
        ws = _get_ws(APPLICATIONS_SHEET_NAME)
        _ensure_headers(ws, APP_HEADERS)
    except Exception:
        return []
    all_data = ws.get_all_values()
    result = []
    for row in all_data[1:]:
        if not row:
            continue
        if status and status != "all":
            expected_label = APP_STATUS_MAP.get(status, "")
            if row[6] != expected_label:
                continue
        result.append(_row_to_app(row))
    return result


def update_application_status(app_id: int, new_status: str) -> bool:
    """Обновить статус заявки. new_status — ключ."""
    try:
        ws = _get_ws(APPLICATIONS_SHEET_NAME)
    except Exception:
        return False
    all_data = ws.get_all_values()
    for idx, row in enumerate(all_data[1:], start=2):
        if row and row[0].isdigit() and int(row[0]) == app_id:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ws.update_cell(idx, 7, APP_STATUS_MAP.get(new_status, APP_STATUS_MAP["new"]))
            ws.update_cell(idx, 9, now)
            logger.info("Application #%s status → %s", app_id, new_status)
            return True
    return False


def check_duplicate_phone(phone: str) -> bool:
    """Проверить, есть ли уже заявка с таким телефоном."""
    try:
        ws = _get_ws(APPLICATIONS_SHEET_NAME)
        _ensure_headers(ws, APP_HEADERS)
    except Exception:
        return False
    phones = ws.col_values(4)[1:]  # столбец Телефон, без заголовка
    return phone in phones


def check_duplicate_user(tg_id: int) -> bool:
    """Проверить, есть ли заявка с таким Telegram ID."""
    try:
        ws = _get_ws(APPLICATIONS_SHEET_NAME)
        _ensure_headers(ws, APP_HEADERS)
    except Exception:
        return False
    ids = ws.col_values(2)[1:]
    return str(tg_id) in ids


def _row_to_app(row: list) -> dict:
    return {
        "id": int(row[0]) if row[0].isdigit() else row[0],
        "telegram_id": int(row[1]) if row[1].isdigit() else row[1],
        "name": row[2],
        "phone": row[3],
        "city": row[4],
        "object_id": row[5],
        "status": row[6],
        "created_at": row[7],
        "updated_at": row[8] if len(row) > 8 else "",
    }


# ═════════════════════  OBJECTS  ═══════════════════════════

OBJ_HEADERS = [
    "ID", "Название", "Цена", "Описание", "Фото (file_id)",
    "Фото (локальный путь)", "Статус", "Дата создания",
]

_next_obj_id = 0


def _get_next_obj_id(ws: Worksheet) -> int:
    global _next_obj_id
    if _next_obj_id == 0:
        values = ws.col_values(1)[1:]
        ids = [int(v) for v in values if v.isdigit()]
        _next_obj_id = max(ids) + 1 if ids else 1
    else:
        _next_obj_id += 1
    return _next_obj_id


def create_object(data: dict) -> int | None:
    """Создать объект аренды. Возвращает ID."""
    try:
        ws = _get_ws(OBJECTS_SHEET_NAME)
        _ensure_headers(ws, OBJ_HEADERS)
    except Exception as exc:
        logger.error("Cannot open objects sheet: %s", exc)
        return None

    obj_id = _get_next_obj_id(ws)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([
        obj_id,
        data["name"],
        data["price"],
        data["description"],
        data.get("photo_file_id", ""),
        data.get("photo_local_path", ""),
        OBJ_STATUS_MAP.get(data.get("status", "available"), OBJ_STATUS_MAP["available"]),
        now,
    ])
    logger.info("Object #%s created: %s", obj_id, data["name"])
    return obj_id


def get_all_objects(status: str | None = None) -> list:
    """Все объекты, опционально по статусу (ключ)."""
    try:
        ws = _get_ws(OBJECTS_SHEET_NAME)
        _ensure_headers(ws, OBJ_HEADERS)
    except Exception:
        return []
    all_data = ws.get_all_values()
    result = []
    for row in all_data[1:]:
        if not row:
            continue
        if status:
            expected_label = OBJ_STATUS_MAP.get(status, "")
            if row[6] != expected_label:
                continue
        result.append(_row_to_obj(row))
    return result


def get_object(obj_id: int) -> dict | None:
    try:
        ws = _get_ws(OBJECTS_SHEET_NAME)
    except Exception:
        return None
    all_data = ws.get_all_values()
    for row in all_data[1:]:
        if row and row[0].isdigit() and int(row[0]) == obj_id:
            return _row_to_obj(row)
    return None


def update_object_field(obj_id: int, field: str, value: str) -> bool:
    """Обновить поле объекта. field — имя колонки (название, цена, описание, статус)."""
    col_map = {
        "name": 2,
        "price": 3,
        "description": 4,
        "photo_file_id": 5,
        "photo_local_path": 6,
        "status_label": 7,
        "status": 7,
    }
    col = col_map.get(field)
    if col is None:
        return False
    try:
        ws = _get_ws(OBJECTS_SHEET_NAME)
    except Exception:
        return False
    all_data = ws.get_all_values()
    for idx, row in enumerate(all_data[1:], start=2):
        if row and row[0].isdigit() and int(row[0]) == obj_id:
            if field == "status":
                value = OBJ_STATUS_MAP.get(value, value)
            ws.update_cell(idx, col, value)
            logger.info("Object #%s %s → %s", obj_id, field, value)
            return True
    return False


def delete_object(obj_id: int) -> bool:
    """Удалить строку объекта."""
    try:
        ws = _get_ws(OBJECTS_SHEET_NAME)
    except Exception:
        return False
    all_data = ws.get_all_values()
    for idx, row in enumerate(all_data[1:], start=2):
        if row and row[0].isdigit() and int(row[0]) == obj_id:
            ws.delete_row(idx)
            logger.info("Object #%s deleted", obj_id)
            return True
    return False


def _row_to_obj(row: list) -> dict:
    return {
        "id": int(row[0]) if row[0].isdigit() else row[0],
        "name": row[1],
        "price": row[2],
        "description": row[3],
        "photo_file_id": row[4],
        "photo_local_path": row[5],
        "status": row[6],
        "created_at": row[7] if len(row) > 7 else "",
    }
