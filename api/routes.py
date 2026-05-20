"""
FastAPI route handlers for the ReelMind API.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ai.analyzer import MistralAnalyzer
from ai.context_builder import build_unified_context
from api.schemas import (
    HealthResponse,
    ProcessReelRequest,
    ProcessReelResponse,
    ReelResponse,
)
from database.connection import get_session
from database.crud import create_reel_record, get_reel_by_id, get_reel_by_url
from extractor.reel_extractor import ReelExtractor
from transcriber.whisper_service import WhisperTranscriber, TranscriptResult
from utils.logger import get_logger
from utils.validators import is_instagram_reel_url
from vector_store.chroma_service import ChromaService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint — verifies service status."""
    health = HealthResponse(status="healthy", service="ReelMind AI", version="1.0.0")

    # Check database connectivity
    try:
        async with get_session() as session:
            await session.execute("SELECT 1" if False else session.get_bind())
        health.database = "connected"
    except Exception:
        health.database = "disconnected"

    # Check ChromaDB
    try:
        chroma = ChromaService()
        health.chromadb = f"connected ({chroma._collection.count()} embeddings)"
    except Exception:
        health.chromadb = "disconnected"

    return health


@router.post("/process-reel", response_model=ProcessReelResponse)
async def process_reel(request: ProcessReelRequest):
    """
    Process an Instagram reel URL via the API.

    This endpoint runs the full pipeline: extract → transcribe →
    analyze → store and returns the structured analysis.
    """
    url = request.url.strip()

    # Validate URL
    if not is_instagram_reel_url(url):
        raise HTTPException(status_code=400, detail="Invalid Instagram Reel URL")

    # Check cache
    try:
        async with get_session() as session:
            existing = await get_reel_by_url(session, url)
            if existing:
                return ProcessReelResponse(
                    success=True,
                    message="Reel already processed (cached)",
                    data=ReelResponse.model_validate(existing),
                )
    except Exception as e:
        logger.warning(f"Cache check failed: {e}")

    # Run processing pipeline
    try:
        extractor = ReelExtractor()
        transcriber = WhisperTranscriber()
        analyzer = MistralAnalyzer()

        # Extract
        reel_data = await extractor.extract(url)

        # Transcribe
        if reel_data.has_audio:
            transcript = await transcriber.transcribe(reel_data.audio_path)
        else:
            transcript = TranscriptResult(text="", success=False, error="No audio")

        # Build context and analyze
        context = build_unified_context(reel_data, transcript)
        analysis = await analyzer.analyze(context)

        # Store in database
        try:
            async with get_session() as session:
                record = await create_reel_record(
                    session=session,
                    url=url,
                    reel_data=reel_data,
                    transcript=transcript,
                    analysis=analysis,
                )
                return ProcessReelResponse(
                    success=True,
                    message="Reel processed successfully",
                    data=ReelResponse.model_validate(record),
                )
        except Exception as e:
            logger.error(f"DB store failed: {e}")
            # Return analysis even if DB fails
            return ProcessReelResponse(
                success=True,
                message="Reel processed (storage failed)",
                data=None,
            )

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/reel/{reel_id}", response_model=ReelResponse)
async def get_reel(reel_id: UUID):
    """Retrieve a previously processed reel by its ID."""
    try:
        async with get_session() as session:
            record = await get_reel_by_id(session, reel_id)
            if not record:
                raise HTTPException(status_code=404, detail="Reel not found")
            return ReelResponse.model_validate(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve reel: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
