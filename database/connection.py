"""
Database connection and session management.

Uses async SQLAlchemy with asyncpg for PostgreSQL.
Provides connection pooling and session factory.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from utils.config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ── Engine & Session Factory ──────────────────────────────────────────

# Create async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False,  # Set True for SQL debugging
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async database session with automatic cleanup.

    Usage:
        async with get_session() as session:
            result = await session.execute(...)

    Yields:
        AsyncSession instance.
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """
    Initialize the database — create all tables.

    Called during application startup.
    """
    from database.models import Base

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db() -> None:
    """
    Close the database engine and all connections.

    Called during application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")
