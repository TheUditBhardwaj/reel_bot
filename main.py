"""
ReelMind AI — Main Application Entrypoint

FastAPI server with Telegram bot webhook integration.
Supports both webhook mode (production) and polling mode (local dev).
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update
from telegram.ext import ApplicationBuilder

from api.routes import router as api_router
from bot.handlers import setup_handlers
from database.connection import close_db, init_db
from utils.config import get_settings
from utils.logger import get_logger, setup_logging

# ── Initialize Settings & Logging ─────────────────────────────────────
settings = get_settings()
setup_logging(level=settings.LOG_LEVEL, env=settings.APP_ENV)
logger = get_logger(__name__)

# ── Telegram Bot Application ─────────────────────────────────────────
bot_app = (
    ApplicationBuilder()
    .token(settings.TELEGRAM_BOT_TOKEN)
    .build()
)


# ── Lifespan Manager ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Startup: Initialize DB, Whisper, ChromaDB, Telegram webhook.
    Shutdown: Cleanup connections and resources.
    """
    logger.info(f"🚀 Starting {settings.APP_NAME} ({settings.APP_ENV})")

    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"⚠️ Database init failed (continuing): {e}")

    # Setup Telegram bot handlers
    setup_handlers(bot_app)

    # Initialize Telegram bot
    await bot_app.initialize()
    await bot_app.start()

    # Set webhook or start polling
    if settings.webhook_enabled:
        webhook_url = f"{settings.WEBHOOK_URL}/webhook"
        await bot_app.bot.set_webhook(
            url=webhook_url,
            secret_token=settings.WEBHOOK_SECRET,
        )
        logger.info(f"✅ Telegram webhook set: {webhook_url}")
    else:
        logger.info("ℹ️ No WEBHOOK_URL set — use polling mode for local dev")
        logger.info("   Run with: python -m bot.polling")

    logger.info(f"✅ {settings.APP_NAME} is ready!")

    yield  # ── Application is running ──

    # Shutdown
    logger.info(f"🛑 Shutting down {settings.APP_NAME}...")

    try:
        await bot_app.stop()
        await bot_app.shutdown()
    except Exception as e:
        logger.error(f"Bot shutdown error: {e}")

    await close_db()
    logger.info("👋 Goodbye!")


# ── FastAPI Application ───────────────────────────────────────────────
app = FastAPI(
    title="ReelMind AI",
    description="AI-powered Instagram Reel summarizer using Mistral AI",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api", tags=["API"])


# ── Telegram Webhook Endpoint ────────────────────────────────────────
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Receive Telegram updates via webhook.

    This endpoint is called by Telegram servers when the bot
    receives a message. The update is passed to the bot application
    for processing.
    """
    # Verify secret token if configured
    if settings.WEBHOOK_SECRET:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if token != settings.WEBHOOK_SECRET:
            logger.warning("Webhook request with invalid secret token")
            return {"status": "unauthorized"}

    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        return {"status": "error"}


@app.get("/")
async def root():
    """Root endpoint — service info."""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


# ── Run ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", settings.PORT))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=not settings.is_production,
        log_level=settings.LOG_LEVEL.lower(),
    )
