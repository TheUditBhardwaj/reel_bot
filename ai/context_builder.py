"""
Multi-context builder for AI analysis.

Merges reel caption, audio transcript, metadata, and hashtags
into a unified context string. This ensures the AI model
considers ALL available information — not just the transcript.
"""

from extractor.reel_extractor import ReelData
from transcriber.whisper_service import TranscriptResult
from utils.logger import get_logger

logger = get_logger(__name__)


def build_unified_context(reel_data: ReelData, transcript: TranscriptResult) -> str:
    """
    Build a unified context string from all available reel data.

    IMPORTANT: This function merges ALL sources (caption, transcript,
    metadata, hashtags) into one context. The AI must analyze the
    full context — not just the transcript alone.

    Args:
        reel_data: Extracted reel metadata and caption.
        transcript: Whisper transcription result.

    Returns:
        Formatted context string for AI analysis.
    """
    sections = []

    # ── Reel Caption / Description ────────────────────────────────────
    caption = reel_data.caption.strip()
    if caption:
        sections.append(
            "=== REEL CAPTION / DESCRIPTION ===\n"
            f"{caption}"
        )
    else:
        sections.append(
            "=== REEL CAPTION / DESCRIPTION ===\n"
            "[No caption available]"
        )

    # ── Audio Transcript ──────────────────────────────────────────────
    if transcript.success and not transcript.is_empty:
        sections.append(
            "=== AUDIO TRANSCRIPT ===\n"
            f"Language Detected: {transcript.language}\n"
            f"{transcript.text}"
        )
    else:
        reason = transcript.error or "No speech detected or audio unavailable"
        sections.append(
            "=== AUDIO TRANSCRIPT ===\n"
            f"[Transcript unavailable: {reason}]"
        )

    # ── Metadata ──────────────────────────────────────────────────────
    metadata_lines = [
        "=== REEL METADATA ===",
        f"Creator/Uploader: {reel_data.uploader or 'Unknown'}",
        f"Platform: {reel_data.platform}",
    ]

    if reel_data.duration:
        minutes = int(reel_data.duration // 60)
        seconds = int(reel_data.duration % 60)
        metadata_lines.append(
            f"Duration: {minutes}m {seconds}s ({reel_data.duration:.0f}s total)"
        )

    if reel_data.view_count:
        metadata_lines.append(f"Views: {reel_data.view_count:,}")

    if reel_data.like_count:
        metadata_lines.append(f"Likes: {reel_data.like_count:,}")

    if reel_data.comment_count:
        metadata_lines.append(f"Comments: {reel_data.comment_count:,}")

    sections.append("\n".join(metadata_lines))

    # ── Hashtags ──────────────────────────────────────────────────────
    if reel_data.hashtags:
        hashtag_str = ", ".join(f"#{tag}" for tag in reel_data.hashtags)
        sections.append(
            f"=== HASHTAGS ===\n{hashtag_str}"
        )

    # ── Title (if different from caption) ─────────────────────────────
    if reel_data.title and reel_data.title != reel_data.caption:
        sections.append(
            f"=== REEL TITLE ===\n{reel_data.title}"
        )

    unified = "\n\n".join(sections)

    logger.info(
        f"Unified context built: {len(unified)} chars, "
        f"has_caption={bool(caption)}, "
        f"has_transcript={transcript.success and not transcript.is_empty}, "
        f"hashtags={len(reel_data.hashtags)}"
    )

    return unified
