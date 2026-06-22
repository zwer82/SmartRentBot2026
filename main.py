"""
SmartRentBot — Telegram bot for rental property management.
aiogram 2.25.1 — supports both polling and webhook (Railway) modes.
"""
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.executor import start_webhook

from bot.config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH, PORT
from bot.handlers import register_all_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup_webhook(dp: Dispatcher):
    """Set webhook on startup."""
    await dp.bot.set_webhook(WEBHOOK_URL)
    logger.info("Webhook set to %s", WEBHOOK_URL)


async def on_shutdown_webhook(dp: Dispatcher):
    """Remove webhook on shutdown."""
    await dp.bot.delete_webhook()
    await dp.storage.close()
    await dp.bot.session.close()
    logger.info("Webhook removed, storage closed.")


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set!")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())

    register_all_handlers(dp)

    # ── Webhook mode (Railway) ──
    if WEBHOOK_URL:
        logger.info("Starting in WEBHOOK mode → %s", WEBHOOK_URL)
        start_webhook(
            dispatcher=dp,
            webhook_path=WEBHOOK_PATH,
            on_startup=on_startup_webhook,
            on_shutdown=on_shutdown_webhook,
            host="0.0.0.0",
            port=PORT,
        )
    # ── Polling mode (local dev) ──
    else:
        logger.info("Starting in POLLING mode...")
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(dp.start_polling())
        except KeyboardInterrupt:
            pass
        finally:
            loop.run_until_complete(dp.storage.close())
            loop.run_until_complete(bot.session.close())


if __name__ == "__main__":
    main()
