"""
Audio transcription service using OpenAI Whisper.

Supports English and Hindi/Hinglish content with configurable
model sizes. Runs Whisper inference in a thread executor to
avoid blocking the async event loop.
"""

import asyncio
import os
from dataclasses import dataclass, field
from typing import Optional

from utils.config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class TranscriptResult:
    """Result from audio transcription."""

    text: str = ""
    language: str = "unknown"
    duration: float = 0.0
    segments: list[dict] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


class WhisperTranscriber:
    """
    Audio transcription using OpenAI's Whisper model.

    The model is loaded lazily on first use to save memory during
    startup. All inference runs in a thread executor so the async
    event loop stays responsive.
    """

    def __init__(self):
        self._model = None
        self._model_name = settings.WHISPER_MODEL
        logger.info(f"WhisperTranscriber initialized (model: {self._model_name})")

    def _load_model(self):
        """
        Lazily load the Whisper model.

        Called on first transcription request. Subsequent calls
        return the cached model.
        """
        if self._model is None:
            import whisper

            logger.info(f"Loading Whisper model '{self._model_name}'...")
            self._model = whisper.load_model(self._model_name)
            logger.info(f"Whisper model '{self._model_name}' loaded successfully")
        return self._model

    def _transcribe_sync(self, audio_path: str) -> TranscriptResult:
        """
        Synchronously transcribe an audio file.

        Args:
            audio_path: Path to the audio file.

        Returns:
            TranscriptResult with transcription details.
        """
        try:
            model = self._load_model()

            # Transcribe with language detection
            # Whisper handles English and Hindi/Hinglish well
            result = model.transcribe(
                audio_path,
                verbose=False,
                task="transcribe",
                # Don't force language — let Whisper auto-detect
                # This handles English, Hindi, and Hinglish content
            )

            # Extract segments with timestamps
            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "start": round(seg["start"], 2),
                    "end": round(seg["end"], 2),
                    "text": seg["text"].strip(),
                })

            # Clean up the transcript text
            text = result.get("text", "").strip()
            language = result.get("language", "unknown")

            logger.info(
                f"Transcription complete: language='{language}', "
                f"length={len(text)} chars, segments={len(segments)}"
            )

            return TranscriptResult(
                text=text,
                language=language,
                duration=segments[-1]["end"] if segments else 0.0,
                segments=segments,
                success=True,
            )

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return TranscriptResult(
                text="",
                success=False,
                error=str(e),
            )

    async def transcribe(self, audio_path: str) -> TranscriptResult:
        """
        Transcribe an audio file asynchronously.

        Runs Whisper inference in a thread executor to avoid
        blocking the event loop.

        Args:
            audio_path: Path to the audio file to transcribe.

        Returns:
            TranscriptResult with transcription text and metadata.
        """
        if not audio_path or not os.path.exists(audio_path):
            logger.warning(f"Audio file not found: {audio_path}")
            return TranscriptResult(
                text="",
                success=False,
                error="Audio file not found",
            )

        file_size = os.path.getsize(audio_path)
        logger.info(f"Transcribing audio: {audio_path} ({file_size / 1024:.1f} KB)")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._transcribe_sync, audio_path)

        # Clean up the audio file after transcription
        try:
            os.remove(audio_path)
            logger.debug(f"Cleaned up audio file: {audio_path}")
        except OSError as e:
            logger.warning(f"Failed to clean up audio file: {e}")

        return result

    def cleanup(self):
        """Release the Whisper model from memory."""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Whisper model released from memory")
