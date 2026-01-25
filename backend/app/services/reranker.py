"""Cross-encoder reranking service for improved retrieval precision.

Uses a cross-encoder model to rerank initial FAISS retrieval results
for more accurate relevance scoring.
"""

from sentence_transformers import CrossEncoder

from ..config import get_settings
from ..core import get_logger
from ..models import DocumentChunk

logger = get_logger(__name__)


class RerankerService:
    """Cross-encoder reranking for improved retrieval precision."""

    def __init__(self, model_name: str | None = None):
        """Initialize reranker service.

        Args:
            model_name: Cross-encoder model name. Defaults to settings value.
        """
        settings = get_settings()
        self._model_name = model_name or settings.reranker_model
        self._model: CrossEncoder | None = None

    @property
    def model(self) -> CrossEncoder:
        """Lazy-load the cross-encoder model."""
        if self._model is None:
            logger.info("Loading reranker model", model=self._model_name)
            self._model = CrossEncoder(self._model_name)
            logger.info("Reranker model loaded", model=self._model_name)
        return self._model

    def rerank(
        self,
        query: str,
        chunks: list[tuple[DocumentChunk, float]],
        top_k: int = 10,
    ) -> list[tuple[DocumentChunk, float, float]]:
        """Rerank chunks using cross-encoder.

        The cross-encoder scores query-document pairs directly, providing
        more accurate relevance scores than bi-encoder similarity.

        Args:
            query: The search query
            chunks: List of (chunk, faiss_score) tuples from initial retrieval
            top_k: Number of top results to return after reranking

        Returns:
            List of (chunk, faiss_score, rerank_score) tuples sorted by rerank_score
        """
        if not chunks:
            return []

        # Build query-document pairs for cross-encoder
        pairs = [(query, chunk.content) for chunk, _ in chunks]

        logger.debug(
            "Reranking chunks",
            query_length=len(query),
            num_chunks=len(chunks),
            top_k=top_k,
        )

        # Get cross-encoder scores
        rerank_scores = self.model.predict(pairs)

        # Combine with original data
        results = [
            (chunk, faiss_score, float(rerank_score))
            for (chunk, faiss_score), rerank_score in zip(chunks, rerank_scores)
        ]

        # Sort by rerank score descending
        results.sort(key=lambda x: x[2], reverse=True)

        logger.info(
            "Reranking completed",
            input_chunks=len(chunks),
            output_chunks=min(top_k, len(results)),
            top_rerank_score=results[0][2] if results else 0,
        )

        return results[:top_k]


# Singleton instance
_reranker_service: RerankerService | None = None


def get_reranker_service() -> RerankerService:
    """Get the singleton reranker service instance."""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service
