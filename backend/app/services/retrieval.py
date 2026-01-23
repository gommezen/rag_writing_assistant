"""Retrieval service for searching document chunks.

Provides similarity search with threshold filtering and metadata tracking.
"""

import time
from datetime import UTC, datetime

from ..config import get_settings
from ..core import get_logger
from ..models import DocumentChunk, RetrievalMetadata, SourceReference
from ..rag import get_vector_store

logger = get_logger(__name__)


class RetrievalService:
    """Service for retrieving relevant document chunks."""

    def __init__(self):
        """Initialize retrieval service."""
        self.settings = get_settings()
        self.vector_store = get_vector_store()

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
        document_ids: list[str] | None = None,
    ) -> tuple[list[SourceReference], RetrievalMetadata]:
        """Retrieve relevant chunks for a query.

        Args:
            query: Search query
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            document_ids: Optional filter by document IDs

        Returns:
            Tuple of (source references, retrieval metadata)
        """
        top_k = top_k or self.settings.top_k_retrieval
        threshold = threshold if threshold is not None else self.settings.similarity_threshold

        start_time = time.time()

        # Search vector store
        results = self.vector_store.search(
            query=query,
            top_k=top_k,
            threshold=threshold,
            document_ids=document_ids,
        )

        retrieval_time_ms = (time.time() - start_time) * 1000

        # Convert to SourceReferences
        sources = []
        for chunk, score in results:
            source = SourceReference(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                excerpt=self._truncate_excerpt(chunk.content),
                relevance_score=score,
                metadata=chunk.metadata,
            )
            sources.append(source)

        # Build metadata
        metadata = RetrievalMetadata(
            query=query,
            top_k=top_k,
            similarity_threshold=threshold,
            chunks_retrieved=len(results),
            chunks_above_threshold=len([r for r in results if r[1] >= threshold]),
            retrieval_time_ms=retrieval_time_ms,
            timestamp=datetime.now(UTC),
        )

        logger.info(
            "Retrieval completed",
            query_length=len(query),
            results_count=len(sources),
            top_k=top_k,
            threshold=threshold,
            retrieval_time_ms=retrieval_time_ms,
        )

        return sources, metadata

    def retrieve_for_sources(
        self,
        query: str,
        document_ids: list[str] | None = None,
    ) -> list[dict]:
        """Retrieve chunks formatted for prompt context.

        This is a convenience method that returns chunks in the format
        expected by the prompt templates.

        Args:
            query: Search query
            document_ids: Optional filter by document IDs

        Returns:
            List of dicts with 'content' and 'metadata' keys
        """
        sources, _ = self.retrieve(query=query, document_ids=document_ids)

        return [
            {
                "content": self._get_full_content(source),
                "metadata": source.metadata,
            }
            for source in sources
        ]

    def _truncate_excerpt(self, content: str, max_length: int = 200) -> str:
        """Truncate content for display as excerpt."""
        if len(content) <= max_length:
            return content
        return content[:max_length].rsplit(" ", 1)[0] + "..."

    def _get_full_content(self, source: SourceReference) -> str:
        """Get full chunk content from vector store.

        Note: The excerpt is truncated, so we need to get the full content
        from the original chunk for prompt building.
        """
        # Search the vector store's chunks for the matching chunk_id
        for chunk in self.vector_store.chunks:
            if chunk.chunk_id == source.chunk_id:
                return chunk.content
        return source.excerpt  # Fallback to excerpt if not found


# Singleton instance
_retrieval_service: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    """Get the singleton retrieval service instance."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
