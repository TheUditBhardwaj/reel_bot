"""
SQLAlchemy ORM models for the ReelMind database.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, BigInteger
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ReelRecord(Base):
    """Stores processed Instagram Reel data."""

    __tablename__ = "reel_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(2048), unique=True, index=True, nullable=False)
    platform = Column(String(50), default="instagram")
    title = Column(String(500))
    caption = Column(Text)
    uploader = Column(String(255))
    uploader_id = Column(String(255))
    duration = Column(Float)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    hashtags = Column(JSON, default=list)
    transcript = Column(Text)
    transcript_language = Column(String(10))
    summary = Column(Text)
    detailed_summary = Column(Text)
    key_takeaways = Column(JSON, default=list)
    tools_mentioned = Column(JSON, default=list)
    category = Column(String(100), index=True)
    keywords = Column(JSON, default=list)
    action_items = Column(JSON, default=list)
    telegram_chat_id = Column(BigInteger)
    telegram_message_id = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<ReelRecord(id={self.id}, url='{self.url[:50]}...')>"
