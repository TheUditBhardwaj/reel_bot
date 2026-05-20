"""
Telegram response formatter.

Formats the structured AI analysis into a clean,
structured Telegram message without emojis.
"""

from ai.analyzer import AnalysisResult
from utils.logger import get_logger

logger = get_logger(__name__)

# Telegram message limit
MAX_MESSAGE_LENGTH = 4096

SEPARATOR = "─" * 32


def format_telegram_response(analysis: AnalysisResult, use_markdown: bool = True) -> str:
    """
    Format an AnalysisResult into a clean, structured Telegram message.

    No emojis — uses clear section headers and dividers instead.

    Args:
        analysis: The structured AI analysis result.
        use_markdown: Whether to use Markdown formatting (default True).

    Returns:
        Formatted message string ready to send via Telegram.
    """
    sections = []

    # ── Title ─────────────────────────────────────────────────────────
    sections.append(SEPARATOR)
    sections.append(f"  {analysis.title.upper()}")
    sections.append(SEPARATOR)

    # ── Summary ───────────────────────────────────────────────────────
    if analysis.summary:
        sections.append("")
        sections.append("SUMMARY")
        sections.append(analysis.summary)

    # ── Detailed Summary ──────────────────────────────────────────────
    if analysis.detailed_summary:
        sections.append("")
        sections.append("DETAILED SUMMARY")
        sections.append(analysis.detailed_summary)

    # ── Key Takeaways ─────────────────────────────────────────────────
    if analysis.key_takeaways:
        sections.append("")
        sections.append("KEY TAKEAWAYS")
        for i, t in enumerate(analysis.key_takeaways, 1):
            sections.append(f"  {i}. {t}")

    # ── Tools Mentioned ───────────────────────────────────────────────
    if analysis.tools_mentioned:
        sections.append("")
        sections.append("TOOLS MENTIONED")
        for t in analysis.tools_mentioned:
            sections.append(f"  - {t}")

    # ── Category ──────────────────────────────────────────────────────
    if analysis.category:
        sections.append("")
        sections.append(f"CATEGORY: {analysis.category}")

    # ── Keywords ──────────────────────────────────────────────────────
    if analysis.keywords:
        sections.append("")
        sections.append("KEYWORDS")
        sections.append("  " + " | ".join(analysis.keywords))

    # ── Action Items ──────────────────────────────────────────────────
    if analysis.action_items:
        sections.append("")
        sections.append("ACTION ITEMS")
        for i, a in enumerate(analysis.action_items, 1):
            sections.append(f"  {i}. {a}")

    # ── Footer ────────────────────────────────────────────────────────
    sections.append("")
    sections.append(SEPARATOR)
    sections.append("  Powered by ReelMind AI")
    sections.append(SEPARATOR)

    message = "\n".join(sections)

    # Handle message length limit
    if len(message) > MAX_MESSAGE_LENGTH:
        logger.warning(f"Message too long ({len(message)} chars), truncating...")
        message = _truncate_message(message)

    return message


def _truncate_message(message: str) -> str:
    """Truncate a message to fit within Telegram's character limit."""
    footer = f"\n\n[Message truncated]\n{SEPARATOR}\n  Powered by ReelMind AI\n{SEPARATOR}"
    max_content = MAX_MESSAGE_LENGTH - len(footer) - 10
    truncated = message[:max_content]

    # Break at a newline to avoid cutting mid-word
    last_newline = truncated.rfind("\n")
    if last_newline > max_content * 0.7:
        truncated = truncated[:last_newline]

    return truncated + footer


def format_error_message(error_type: str, details: str = "") -> str:
    """
    Format a user-friendly error message.

    Args:
        error_type: Type of error (e.g., "invalid_url", "extraction_failed").
        details: Optional additional error details.

    Returns:
        Formatted error message string.
    """
    error_messages = {
        "invalid_url": (
            "[ERROR] Invalid URL\n\n"
            "That doesn't look like a valid Instagram Reel URL.\n\n"
            "Please send a link like:\n"
            "https://www.instagram.com/reel/ABC123xyz/"
        ),
        "extraction_failed": (
            "[ERROR] Extraction Failed\n\n"
            "Could not extract reel data.\n\n"
            "Possible reasons:\n"
            "  - The reel is private or deleted\n"
            "  - Instagram is rate-limiting requests\n"
            "  - The URL format is not supported\n\n"
            "Please try again later."
        ),
        "transcription_failed": (
            "[WARNING] Transcription Failed\n\n"
            "Audio transcription failed, but the caption "
            "and metadata will still be analyzed."
        ),
        "analysis_failed": (
            "[ERROR] Analysis Failed\n\n"
            "The AI service might be temporarily unavailable.\n"
            "Please try again in a moment."
        ),
        "processing_error": (
            "[ERROR] Processing Failed\n\n"
            f"Details: {details}\n\n"
            "Please try again or contact support."
        ),
        "rate_limit": (
            "[RATE LIMIT]\n\n"
            "You're sending requests too quickly.\n"
            "Please wait a moment before sending another reel."
        ),
    }

    return error_messages.get(error_type, f"[ERROR] {details}")
