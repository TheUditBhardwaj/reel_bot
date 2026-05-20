"""
CRUD operations for the reel_records table.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.analyzer import AnalysisResult
from database.models import ReelRecord
from extractor.reel_extractor import ReelData
from transcriber.whisper_service import TranscriptResult
from utils.logger import get_logger

logger = get_logger(__name__)


async def create_reel_record(
    session: AsyncSession,
    url: str,
    reel_data: ReelData,
    transcript: TranscriptResult,
    analysis: AnalysisResult,
    chat_id: int = None,
    message_id: int = None,
) -> ReelRecord:
    """Create a new reel record from all pipeline outputs."""
    record = ReelRecord(
        url=url,
        platform=reel_data.platform,
        title=analysis.title,
        caption=reel_data.caption,
        uploader=reel_data.uploader,
        uploader_id=reel_data.uploader_id,
        duration=reel_data.duration,
        view_count=reel_data.view_count,
        like_count=reel_data.like_count,
        comment_count=reel_data.comment_count,
        hashtags=reel_data.hashtags,
        transcript=transcript.text if transcript.success else None,
        transcript_language=transcript.language if transcript.success else None,
        summary=analysis.summary,
        detailed_summary=analysis.detailed_summary,
        key_takeaways=analysis.key_takeaways,
        tools_mentioned=analysis.tools_mentioned,
        category=analysis.category,
        keywords=analysis.keywords,
        action_items=analysis.action_items,
        telegram_chat_id=chat_id,
        telegram_message_id=message_id,
    )
    session.add(record)
    await session.flush()
    logger.info(f"Created reel record: {record.id}")
    return record


async def get_reel_by_url(session: AsyncSession, url: str) -> Optional[ReelRecord]:
    """Look up a reel record by its URL (cache check)."""
    stmt = select(ReelRecord).where(ReelRecord.url == url)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_reel_by_id(session: AsyncSession, reel_id: UUID) -> Optional[ReelRecord]:
    """Look up a reel record by its UUID."""
    stmt = select(ReelRecord).where(ReelRecord.id == reel_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_reels(
    session: AsyncSession, skip: int = 0, limit: int = 20
) -> list[ReelRecord]:
    """List reel records with pagination."""
    stmt = (
        select(ReelRecord)
        .order_by(ReelRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
