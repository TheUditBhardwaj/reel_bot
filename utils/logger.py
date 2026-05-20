"""
Centralized logging configuration.

Provides structured JSON logs in production and
human-readable logs in development.
"""

import logging
import sys
from typing import Optional


def _get_formatter(env: str) -> logging.Formatter:
    """Return appropriate formatter based on environment."""
    if env == "production":
        # JSON-style structured log for production log aggregators
        return logging.Formatter(
            '{"time":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","message":"%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    # Human-readable format for development
    return logging.Formatter(
        "%(asctime)s │ %(levelname)-8s │ %(name)-25s │ %(message)s",
        datefmt="%H:%M:%S",
    )


def setup_logging(level: str = "INFO", env: str = "development") -> None:
    """
    Configure root logger with the appropriate handler and formatter.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        env: Application environment (development or production).
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates on re-init
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_get_formatter(env))
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "chromadb", "yt_dlp", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a named logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module).

    Returns:
        Configured logging.Logger instance.
    """
    return logging.getLogger(name or "reelmind")
