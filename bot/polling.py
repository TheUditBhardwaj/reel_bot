"""
Telegram bot polling mode for local development.

Use this instead of webhooks when running locally.
Run with: python -m bot.polling
"""

import asyncio

from telegram.ext import ApplicationBuilder

from bot.handlers import setup_handlers
from database.connection import init_db
from utils.config import get_settings
from utils.logger import get_logger, setup_logging

settings = get_settings()
setup_logging(level=settings.LOG_LEVEL, env=settings.APP_ENV)
logger = get_logger(__name__)


async def main():
    """Start the bot in polling mode."""
    logger.info(f"🚀 Starting {settings.APP_NAME} in POLLING mode")

    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.warning(f"⚠️ Database init failed (continuing): {e}")

    # Build and configure bot
    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    setup_handlers(app)

    # Start polling
    logger.info("✅ Bot is running! Send a message on Telegram.")
    logger.info("   Press Ctrl+C to stop.")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # Keep running until interrupted
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("👋 Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
