"""
Pydantic schemas for FastAPI request/response models.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ProcessReelRequest(BaseModel):
    """Request body for POST /process-reel."""
    url: str = Field(..., description="Instagram Reel URL to process")


class ReelResponse(BaseModel):
    """Response body for reel data."""
    id: UUID
    url: str
    title: Optional[str] = None
    caption: Optional[str] = None
    uploader: Optional[str] = None
    duration: Optional[float] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    detailed_summary: Optional[str] = None
    key_takeaways: list[str] = []
    tools_mentioned: list[str] = []
    category: Optional[str] = None
    keywords: list[str] = []
    action_items: list[str] = []
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    """Response body for GET /health."""
    status: str = "healthy"
    service: str = "ReelMind AI"
    version: str = "1.0.0"
    database: str = "unknown"
    chromadb: str = "unknown"


class ProcessReelResponse(BaseModel):
    """Response body for POST /process-reel."""
    success: bool
    message: str
    data: Optional[ReelResponse] = None
