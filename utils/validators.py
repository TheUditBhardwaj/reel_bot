"""
URL validation utilities for Instagram Reels and other platforms.

Designed to be extensible for future support of YouTube Shorts,
TikTok, LinkedIn videos, etc.
"""

import re
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# ── Instagram URL patterns ────────────────────────────────────────────
# Matches:
#   https://www.instagram.com/reel/ABC123xyz/
#   https://instagram.com/p/ABC123xyz/
#   https://www.instagram.com/reels/ABC123xyz/?igsh=...
#   https://instagr.am/reel/ABC123xyz/
INSTAGRAM_REEL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:instagram\.com|instagr\.am)"
    r"/(?:reel|reels|p)/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)

# Generic Instagram URL (broader match for edge cases)
INSTAGRAM_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:instagram\.com|instagr\.am)/",
    re.IGNORECASE,
)

# ── Future platform patterns ──────────────────────────────────────────
YOUTUBE_SHORTS_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/shorts|youtu\.be)/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)

TIKTOK_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:tiktok\.com|vm\.tiktok\.com)/",
    re.IGNORECASE,
)


def is_instagram_reel_url(url: str) -> bool:
    """
    Check if the provided URL is a valid Instagram reel/post URL.

    Args:
        url: The URL string to validate.

    Returns:
        True if the URL matches Instagram reel/post patterns.
    """
    if not url or not isinstance(url, str):
        return False
    return bool(INSTAGRAM_REEL_PATTERN.search(url.strip()))


def extract_reel_shortcode(url: str) -> Optional[str]:
    """
    Extract the shortcode (unique identifier) from an Instagram reel URL.

    Args:
        url: Instagram reel URL.

    Returns:
        The shortcode string, or None if not found.
    """
    match = INSTAGRAM_REEL_PATTERN.search(url.strip())
    return match.group(1) if match else None


def extract_urls_from_text(text: str) -> list[str]:
    """
    Extract all Instagram reel URLs from a text message.

    Args:
        text: The message text to search.

    Returns:
        List of Instagram reel URLs found in the text.
    """
    if not text:
        return []

    # Find all URLs in the text
    url_pattern = re.compile(r"https?://\S+", re.IGNORECASE)
    all_urls = url_pattern.findall(text)

    # Filter to only Instagram reel URLs
    reel_urls = [url for url in all_urls if is_instagram_reel_url(url)]

    if reel_urls:
        logger.info(f"Found {len(reel_urls)} Instagram reel URL(s) in message")
    return reel_urls


def get_platform(url: str) -> Optional[str]:
    """
    Detect which platform a URL belongs to.

    Args:
        url: The URL to identify.

    Returns:
        Platform name string or None if unrecognized.
    """
    url = url.strip()
    if INSTAGRAM_REEL_PATTERN.search(url):
        return "instagram"
    if YOUTUBE_SHORTS_PATTERN.search(url):
        return "youtube_shorts"
    if TIKTOK_PATTERN.search(url):
        return "tiktok"
    return None
