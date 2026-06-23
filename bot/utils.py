import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def download_photo(bot, file_id: str, dest_dir: str, obj_id: int) -> Optional[str]:
    """
    Скачать фото по file_id в локальную папку.
    Возвращает путь к файлу или None.
    """
    try:
        file = bot.get_file(file_id)
        ext = os.path.splitext(file.file_path or ".jpg")[1] or ".jpg"
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, f"object_{obj_id}{ext}")
        bot.download_file(file.file_path, dest)
        logger.info("Photo saved: %s", dest)
        return dest
    except Exception as exc:
        logger.error("Failed to download photo: %s", exc)
        return None


def paginate(items: list, page: int, per_page: int = 10):
    """Разбить список на страницы. Возвращает (срез, всего_страниц)."""
    total = len(items)
    pages = max(1, (total + per_page - 1) // per_page)
    start = page * per_page
    end = start + per_page
    return items[start:end], pages
