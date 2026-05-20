"""
Telegram bot message handlers.

Handles /start, /help commands and Instagram reel URL messages.
Orchestrates the full processing pipeline: extract → transcribe →
analyze → store → reply.
"""

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ai.analyzer import AnalysisError, MistralAnalyzer
from ai.context_builder import build_unified_context
from bot.formatter import format_error_message, format_telegram_response
from database.crud import create_reel_record, get_reel_by_url
from database.connection import get_session
from extractor.reel_extractor import ExtractionError, ReelExtractor
from notion.sync import NotionSync
from transcriber.whisper_service import WhisperTranscriber
from utils.config import get_settings
from utils.logger import get_logger
from utils.validators import extract_urls_from_text, is_instagram_reel_url
from vector_store.chroma_service import ChromaService

logger = get_logger(__name__)
settings = get_settings()

# ── Shared service instances (initialized in setup_handlers) ──────────
_extractor: ReelExtractor = None  # type: ignore
_transcriber: WhisperTranscriber = None  # type: ignore
_analyzer: MistralAnalyzer = None  # type: ignore
_chroma: ChromaService = None  # type: ignore
_notion: NotionSync = None  # type: ignore


def get_services():
    """Get or initialize shared service instances."""
    global _extractor, _transcriber, _analyzer, _chroma, _notion

    if _extractor is None:
        _extractor = ReelExtractor()
    if _transcriber is None:
        _transcriber = WhisperTranscriber()
    if _analyzer is None:
        _analyzer = MistralAnalyzer()
    if _chroma is None:
        _chroma = ChromaService()
    if _notion is None and settings.notion_enabled:
        _notion = NotionSync()

    return _extractor, _transcriber, _analyzer, _chroma, _notion


# ── Command Handlers ──────────────────────────────────────────────────


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command — welcome message."""
    welcome = (
        "Welcome to ReelMind AI\n\n"
        "I analyze Instagram Reels and provide AI-powered summaries, "
        "key takeaways, and actionable insights.\n\n"
        "HOW TO USE:\n"
        "Simply send me an Instagram Reel URL and I'll do the rest.\n\n"
        "EXAMPLE:\n"
        "https://www.instagram.com/reel/ABC123xyz/\n\n"
        "I analyze the full context -- caption, audio transcript, "
        "metadata, and hashtags -- to give you comprehensive insights.\n\n"
        "Type /help for more information."
    )
    await update.message.reply_text(welcome)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command — usage instructions."""
    help_text = (
        "REELMIND AI - HELP\n\n"
        "SEND A REEL URL:\n"
        "Paste any Instagram Reel link and I'll analyze it.\n\n"
        "WHAT I PROVIDE:\n"
        "  - AI-generated title & summary\n"
        "  - Key takeaways\n"
        "  - Tools/platforms mentioned\n"
        "  - Content category & keywords\n"
        "  - Actionable insights\n\n"
        "SUPPORTED FORMATS:\n"
        "  - instagram.com/reel/...\n"
        "  - instagram.com/reels/...\n"
        "  - instagram.com/p/...\n\n"
        "COMING SOON:\n"
        "  - YouTube Shorts\n"
        "  - TikTok\n"
        "  - LinkedIn Videos"
    )
    await update.message.reply_text(help_text)


# ── Main Message Handler ─────────────────────────────────────────────


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming text messages.

    Detects Instagram reel URLs and triggers the processing pipeline.
    """
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    chat_id = update.message.chat_id

    # Extract Instagram reel URLs from the message
    reel_urls = extract_urls_from_text(text)

    if not reel_urls:
        # Check if the message looks like it could be a URL attempt
        if "instagram" in text.lower() or "reel" in text.lower():
            await update.message.reply_text(
                format_error_message("invalid_url")
            )
        else:
            await update.message.reply_text(
                "Send me an Instagram Reel URL and I'll analyze it for you.\n\n"
                "Example: https://www.instagram.com/reel/ABC123xyz/"
            )
        return

    # Process the first reel URL found
    url = reel_urls[0]
    logger.info(f"Processing reel URL from chat {chat_id}: {url}")

    await _process_reel(update, url)


async def _process_reel(update: Update, url: str) -> None:
    """
    Full reel processing pipeline.

    Steps:
    1. Check cache (DB lookup by URL)
    2. Send processing acknowledgment
    3. Extract reel data (yt-dlp)
    4. Transcribe audio (Whisper)
    5. Build unified context
    6. AI analysis (Mistral)
    7. Store in PostgreSQL + ChromaDB
    8. Send formatted response
    9. Optional: sync to Notion

    Args:
        update: Telegram update object.
        url: Instagram reel URL to process.
    """
    extractor, transcriber, analyzer, chroma, notion = get_services()
    chat_id = update.message.chat_id

    # ── Step 1: Check cache ───────────────────────────────────────────
    try:
        async with get_session() as session:
            existing = await get_reel_by_url(session, url)
            if existing:
                logger.info(f"Cache hit for URL: {url}")
                from ai.analyzer import AnalysisResult

                cached_result = AnalysisResult(
                    title=existing.title or "Untitled",
                    summary=existing.summary or "",
                    detailed_summary=existing.detailed_summary or "",
                    key_takeaways=existing.key_takeaways or [],
                    tools_mentioned=existing.tools_mentioned or [],
                    category=existing.category or "Other",
                    keywords=existing.keywords or [],
                    action_items=existing.action_items or [],
                )
                response = format_telegram_response(cached_result, use_markdown=False)
                response = "[CACHED RESULT]\n\n" + response
                await update.message.reply_text(response)
                return
    except Exception as e:
        logger.warning(f"Cache lookup failed (continuing): {e}")

    # ── Step 2: Send processing acknowledgment ────────────────────────
    status_msg = await update.message.reply_text(
        "Processing your reel...\n\n"
        "[1/4] Extracting metadata & audio\n"
        "This may take 30-60 seconds."
    )

    try:
        # ── Step 3: Extract reel data ─────────────────────────────────
        try:
            reel_data = await extractor.extract(url)
        except ExtractionError:
            await status_msg.edit_text(format_error_message("extraction_failed"))
            return

        await status_msg.edit_text(
            "Processing your reel...\n\n"
            "[1/4] Metadata extracted\n"
            "[2/4] Transcribing audio..."
        )

        # ── Step 4: Transcribe audio ──────────────────────────────────
        if reel_data.has_audio:
            transcript = await transcriber.transcribe(reel_data.audio_path)
        else:
            from transcriber.whisper_service import TranscriptResult

            transcript = TranscriptResult(
                text="",
                success=False,
                error="No audio available",
            )

        await status_msg.edit_text(
            "Processing your reel...\n\n"
            "[1/4] Metadata extracted\n"
            "[2/4] Audio transcribed\n"
            "[3/4] Generating AI analysis..."
        )

        # ── Step 5: Build unified context ─────────────────────────────
        context = build_unified_context(reel_data, transcript)

        # ── Step 6: AI analysis ───────────────────────────────────────
        try:
            analysis = await analyzer.analyze(context)
        except AnalysisError:
            await status_msg.edit_text(format_error_message("analysis_failed"))
            return

        # ── Step 7: Store in databases ────────────────────────────────
        reel_record_id = None
        try:
            async with get_session() as session:
                record = await create_reel_record(
                    session=session,
                    url=url,
                    reel_data=reel_data,
                    transcript=transcript,
                    analysis=analysis,
                    chat_id=chat_id,
                    message_id=update.message.message_id,
                )
                reel_record_id = str(record.id)
                logger.info(f"Reel stored in PostgreSQL: {reel_record_id}")
        except Exception as e:
            logger.error(f"Database storage failed (continuing): {e}")

        # Store embeddings in ChromaDB
        try:
            chroma.store_embedding(
                reel_id=reel_record_id or url,
                transcript=transcript.text,
                summary=analysis.summary,
                metadata={
                    "url": url,
                    "category": analysis.category,
                    "title": analysis.title,
                },
            )
            logger.info("Embeddings stored in ChromaDB")
        except Exception as e:
            logger.error(f"ChromaDB storage failed (continuing): {e}")

        # ── Step 8: Send formatted response ───────────────────────────
        response = format_telegram_response(analysis, use_markdown=False)
        await status_msg.edit_text(response)

        # ── Step 9: Notion sync (optional, non-blocking) ─────────────
        if notion and settings.notion_enabled:
            try:
                await notion.sync_reel(analysis, url)
                logger.info("Reel synced to Notion")
            except Exception as e:
                logger.error(f"Notion sync failed (non-critical): {e}")

    except Exception as e:
        logger.error(f"Unexpected error processing reel: {e}", exc_info=True)
        try:
            await status_msg.edit_text(
                format_error_message("processing_error", str(e))
            )
        except Exception:
            pass


# ── Handler Registration ──────────────────────────────────────────────


def setup_handlers(application: Application) -> None:
    """
    Register all handlers with the Telegram bot application.

    Args:
        application: python-telegram-bot Application instance.
    """
    # Initialize services
    get_services()

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Message handler for all text messages
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("Telegram bot handlers registered")
