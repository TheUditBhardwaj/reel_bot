"""
Mistral AI analysis service via NVIDIA API.

Sends the unified reel context to Mistral AI (hosted on NVIDIA)
and parses the structured JSON response into a Pydantic model.
"""

import json

import httpx
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ai.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from utils.config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# NVIDIA API endpoint for chat completions
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


class AnalysisResult(BaseModel):
    """Structured analysis output from Mistral AI."""

    title: str = Field(default="Untitled", description="Generated title for the reel")
    summary: str = Field(default="", description="Concise 2-3 sentence summary")
    detailed_summary: str = Field(
        default="", description="Comprehensive 4-6 sentence summary"
    )
    key_takeaways: list[str] = Field(
        default_factory=list, description="3-5 key takeaways"
    )
    tools_mentioned: list[str] = Field(
        default_factory=list, description="Tools/platforms mentioned"
    )
    category: str = Field(default="Other", description="Content category")
    keywords: list[str] = Field(
        default_factory=list, description="5-8 relevant keywords"
    )
    action_items: list[str] = Field(
        default_factory=list, description="2-4 actionable items"
    )


class MistralAnalyzer:
    """
    AI-powered content analyzer using Mistral AI via NVIDIA API.

    Sends the unified context (caption + transcript + metadata + hashtags)
    to NVIDIA's hosted Mistral model and parses the structured JSON output.
    """

    def __init__(self):
        self._api_key = settings.NVIDIA_API_KEY
        self._model = settings.NVIDIA_MODEL
        self._client = httpx.AsyncClient(timeout=120.0)
        logger.info(f"MistralAnalyzer initialized (model: {self._model})")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        before_sleep=lambda retry_state: logger.warning(
            f"NVIDIA API attempt {retry_state.attempt_number} failed, retrying..."
        ),
    )
    async def analyze(self, context: str) -> AnalysisResult:
        """
        Analyze unified reel context using Mistral AI via NVIDIA API.

        Args:
            context: The unified context string built from caption,
                     transcript, metadata, and hashtags.

        Returns:
            AnalysisResult with structured summary and insights.

        Raises:
            AnalysisError: If analysis fails after all retries.
        """
        logger.info(f"Sending context to NVIDIA Mistral API ({len(context)} chars)")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_PROMPT_TEMPLATE.format(context=context),
                },
            ],
            "max_tokens": 2048,
            "temperature": 0.15,
            "top_p": 1.00,
            "frequency_penalty": 0.00,
            "presence_penalty": 0.00,
            "stream": False,
        }

        try:
            response = await self._client.post(
                NVIDIA_API_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

            data = response.json()

            # Extract the response content
            content = data["choices"][0]["message"]["content"]
            logger.debug(f"NVIDIA Mistral raw response: {content[:200]}...")

            # Parse JSON response
            result = self._parse_response(content)
            logger.info(
                f"Analysis complete: title='{result.title[:50]}', "
                f"category='{result.category}', "
                f"takeaways={len(result.key_takeaways)}"
            )
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"NVIDIA API HTTP error {e.response.status_code}: {e.response.text[:300]}")
            raise AnalysisError(f"NVIDIA API error ({e.response.status_code}): {e.response.text[:200]}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse NVIDIA response as JSON: {e}")
            raise AnalysisError(f"Invalid JSON response from NVIDIA API: {e}") from e
        except Exception as e:
            logger.error(f"NVIDIA Mistral analysis failed: {e}")
            raise AnalysisError(f"AI analysis failed: {e}") from e

    def _parse_response(self, content: str) -> AnalysisResult:
        """
        Parse the raw JSON response into an AnalysisResult.

        Handles edge cases where the model may wrap JSON in markdown
        code blocks or return partial data.

        Args:
            content: Raw response string from the model.

        Returns:
            Parsed AnalysisResult model.
        """
        # Strip markdown code blocks if present
        cleaned = content.strip()
        if cleaned.startswith("```"):
            # Remove ```json and ``` wrappers
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        data = json.loads(cleaned)

        # Normalize field names (handle case variations)
        normalized = {}
        field_mappings = {
            "title": ["title", "Title"],
            "summary": ["summary", "Summary", "brief_summary"],
            "detailed_summary": [
                "detailed_summary",
                "Detailed_Summary",
                "detailed",
                "long_summary",
            ],
            "key_takeaways": [
                "key_takeaways",
                "Key_Takeaways",
                "takeaways",
                "key_points",
            ],
            "tools_mentioned": [
                "tools_mentioned",
                "Tools_Mentioned",
                "tools",
                "platforms",
            ],
            "category": ["category", "Category", "content_category"],
            "keywords": ["keywords", "Keywords", "tags"],
            "action_items": [
                "action_items",
                "Action_Items",
                "actions",
                "recommendations",
            ],
        }

        for target_key, source_keys in field_mappings.items():
            for source_key in source_keys:
                if source_key in data:
                    normalized[target_key] = data[source_key]
                    break

        return AnalysisResult(**normalized)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


class AnalysisError(Exception):
    """Raised when AI analysis fails."""
    pass
