"""
Instagram Reel extraction using yt-dlp.

Extracts metadata (caption, hashtags, uploader info) and downloads
audio for transcription. Designed for extensibility to support
YouTube Shorts, TikTok, and LinkedIn videos in the future.
"""

import asyncio
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from typing import Optional

import yt_dlp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from utils.config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class ReelData:
    """Structured data extracted from an Instagram reel."""

    url: str
    title: str = ""
    caption: str = ""
    uploader: str = ""
    uploader_id: str = ""
    duration: float = 0.0
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    timestamp: Optional[int] = None
    hashtags: list[str] = field(default_factory=list)
    audio_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    platform: str = "instagram"

    @property
    def has_audio(self) -> bool:
        return self.audio_path is not None and os.path.exists(self.audio_path or "")


def _extract_hashtags(text: str) -> list[str]:
    """
    Extract hashtags from caption/description text.

    Args:
        text: The caption or description text.

    Returns:
        List of hashtag strings (without the # symbol).
    """
    if not text:
        return []
    return list(set(re.findall(r"#(\w+)", text)))


class ReelExtractor:
    """
    Extracts metadata and audio from Instagram Reels using yt-dlp.

    Supports cookie-based authentication for private/restricted content.
    Runs yt-dlp in a thread executor to avoid blocking the async event loop.
    """

    def __init__(self):
        self.download_dir = settings.DOWNLOAD_DIR
        os.makedirs(self.download_dir, exist_ok=True)

    def _get_base_opts(self) -> dict:
        """Return base yt-dlp options shared across operations."""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": 30,
            "retries": 3,
            # User-agent to avoid blocks
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        }

        # Add cookie file if configured (for private reels)
        if settings.COOKIE_FILE and os.path.exists(settings.COOKIE_FILE):
            opts["cookiefile"] = settings.COOKIE_FILE
            logger.debug("Using cookie file for authentication")

        return opts

    def _extract_metadata_sync(self, url: str) -> dict:
        """
        Synchronously extract metadata without downloading.

        Args:
            url: The Instagram reel URL.

        Returns:
            Raw metadata dictionary from yt-dlp.

        Raises:
            yt_dlp.utils.DownloadError: If extraction fails.
        """
        opts = self._get_base_opts()
        opts["skip_download"] = True

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info or {}

    def _download_audio_sync(self, url: str) -> str:
        """
        Synchronously download audio from the reel.

        Args:
            url: The Instagram reel URL.

        Returns:
            Path to the downloaded audio file.

        Raises:
            yt_dlp.utils.DownloadError: If download fails.
        """
        audio_filename = f"reel_{uuid.uuid4().hex[:12]}"
        output_path = os.path.join(self.download_dir, audio_filename)

        opts = self._get_base_opts()
        opts.update({
            "format": "bestaudio/best",
            "outtmpl": f"{output_path}.%(ext)s",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128",
                }
            ],
        })

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        # Find the downloaded file (extension may vary)
        mp3_path = f"{output_path}.mp3"
        if os.path.exists(mp3_path):
            logger.info(f"Audio downloaded: {mp3_path}")
            return mp3_path

        # Fallback: find any file matching the pattern
        for ext in ("mp3", "m4a", "wav", "opus", "webm"):
            candidate = f"{output_path}.{ext}"
            if os.path.exists(candidate):
                logger.info(f"Audio downloaded: {candidate}")
                return candidate

        raise FileNotFoundError(f"Downloaded audio not found at {output_path}.*")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((yt_dlp.utils.DownloadError, ConnectionError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Reel extraction attempt {retry_state.attempt_number} failed, retrying..."
        ),
    )
    async def extract(self, url: str) -> ReelData:
        """
        Extract metadata and download audio from an Instagram reel.

        This is the main entry point. Runs yt-dlp in a thread executor
        to keep the async event loop free.

        Args:
            url: The Instagram reel URL.

        Returns:
            ReelData object with all extracted information.

        Raises:
            ExtractionError: If extraction fails after all retries.
        """
        logger.info(f"Extracting reel: {url}")
        loop = asyncio.get_event_loop()

        # Step 1: Extract metadata
        try:
            info = await loop.run_in_executor(None, self._extract_metadata_sync, url)
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            raise ExtractionError(f"Failed to extract reel metadata: {e}") from e

        # Parse metadata into ReelData
        caption = info.get("description", "") or info.get("title", "") or ""
        reel_data = ReelData(
            url=url,
            title=info.get("title", "Untitled Reel"),
            caption=caption,
            uploader=info.get("uploader", info.get("channel", "Unknown")),
            uploader_id=info.get("uploader_id", info.get("channel_id", "")),
            duration=float(info.get("duration", 0) or 0),
            view_count=int(info.get("view_count", 0) or 0),
            like_count=int(info.get("like_count", 0) or 0),
            comment_count=int(info.get("comment_count", 0) or 0),
            timestamp=info.get("timestamp"),
            hashtags=_extract_hashtags(caption),
            thumbnail_url=info.get("thumbnail"),
            platform="instagram",
        )

        logger.info(
            f"Metadata extracted: title='{reel_data.title[:50]}', "
            f"uploader='{reel_data.uploader}', duration={reel_data.duration}s, "
            f"hashtags={len(reel_data.hashtags)}"
        )

        # Step 2: Download audio
        try:
            audio_path = await loop.run_in_executor(
                None, self._download_audio_sync, url
            )
            reel_data.audio_path = audio_path
        except Exception as e:
            logger.warning(f"Audio download failed (will proceed without): {e}")
            # Continue without audio — caption-only analysis is still valuable

        return reel_data


class ExtractionError(Exception):
    """Raised when reel extraction fails after all retries."""
    pass
