"""
ChromaDB vector store for semantic search over reel embeddings.
"""

from utils.config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ChromaService:
    """
    Manages ChromaDB collection for reel transcript and summary embeddings.
    Uses the default embedding function (all-MiniLM-L6-v2).
    """

    def __init__(self):
        import chromadb

        self._client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self._collection = self._client.get_or_create_collection(
            name="reel_embeddings",
            metadata={"description": "ReelMind AI reel embeddings"},
        )
        logger.info(
            f"ChromaDB initialized: {self._collection.count()} existing embeddings"
        )

    def store_embedding(
        self,
        reel_id: str,
        transcript: str,
        summary: str,
        metadata: dict = None,
    ) -> None:
        """Store reel transcript + summary as an embedding."""
        # Combine transcript and summary for richer embedding
        document = ""
        if transcript:
            document += f"Transcript: {transcript}\n\n"
        if summary:
            document += f"Summary: {summary}"

        if not document.strip():
            logger.warning(f"Skipping empty document for reel {reel_id}")
            return

        meta = metadata or {}
        meta["reel_id"] = reel_id

        self._collection.upsert(
            ids=[reel_id],
            documents=[document],
            metadatas=[meta],
        )
        logger.info(f"Embedding stored for reel: {reel_id}")

    def search_similar(self, query: str, n_results: int = 5) -> list[dict]:
        """Search for semantically similar reels."""
        if self._collection.count() == 0:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=min(n_results, self._collection.count()),
        )

        similar = []
        for i, doc_id in enumerate(results["ids"][0]):
            similar.append({
                "id": doc_id,
                "document": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })

        return similar
