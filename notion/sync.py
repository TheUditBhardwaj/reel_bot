"""
Optional Notion integration for syncing reel summaries.

Creates entries in a Notion database with the AI analysis results.
Only active when NOTION_API_KEY and NOTION_DATABASE_ID are set.
"""

import asyncio

from ai.analyzer import AnalysisResult
from utils.config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class NotionSync:
    """Syncs reel analysis results to a Notion database."""

    def __init__(self):
        if not settings.notion_enabled:
            logger.info("Notion sync disabled (missing API key or database ID)")
            self._client = None
            return

        from notion_client import Client

        self._client = Client(auth=settings.NOTION_API_KEY)
        self._database_id = settings.NOTION_DATABASE_ID
        logger.info("NotionSync initialized")

    async def sync_reel(self, analysis: AnalysisResult, url: str) -> None:
        """Create a Notion page for the analyzed reel."""
        if not self._client:
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._create_page_sync, analysis, url)

    def _create_page_sync(self, analysis: AnalysisResult, url: str) -> None:
        """Synchronously create a Notion database entry."""
        try:
            takeaways_text = "\n".join(f"• {t}" for t in analysis.key_takeaways)
            tools_text = ", ".join(analysis.tools_mentioned) if analysis.tools_mentioned else "None"

            properties = {
                "Title": {
                    "title": [{"text": {"content": analysis.title[:100]}}]
                },
                "Summary": {
                    "rich_text": [{"text": {"content": analysis.summary[:2000]}}]
                },
                "Category": {
                    "select": {"name": analysis.category}
                },
                "URL": {
                    "url": url
                },
                "Tools": {
                    "rich_text": [{"text": {"content": tools_text[:2000]}}]
                },
                "Keywords": {
                    "rich_text": [{"text": {"content": ", ".join(analysis.keywords)[:2000]}}]
                },
            }

            # Create page with body content
            children = [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "Key Takeaways"}}]
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": takeaways_text}}]
                    },
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "Detailed Summary"}}]
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": analysis.detailed_summary[:2000]}}]
                    },
                },
            ]

            # Add action items if present
            if analysis.action_items:
                children.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "Action Items"}}]
                    },
                })
                for item in analysis.action_items:
                    children.append({
                        "object": "block",
                        "type": "to_do",
                        "to_do": {
                            "rich_text": [{"text": {"content": item}}],
                            "checked": False,
                        },
                    })

            self._client.pages.create(
                parent={"database_id": self._database_id},
                properties=properties,
                children=children,
            )
            logger.info(f"Notion page created: {analysis.title[:50]}")

        except Exception as e:
            logger.error(f"Failed to create Notion page: {e}")
            raise
