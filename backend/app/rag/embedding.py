"""Embedding generation using Ollama.

Uses local Ollama models for privacy-preserving embeddings.
"""

from langchain_ollama import OllamaEmbeddings

from ..config import get_settings
from ..core import EmbeddingError, get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating embeddings using Ollama."""

    def __init__(self, model: str | None = None, base_url: str | None = None):
        """Initialize embedding service.

        Args:
            model: Ollama embedding model name. Defaults to settings value.
            base_url: Ollama API base URL. Defaults to settings value.
        """
        settings = get_settings()
        self.model = model or settings.embedding_model
        self.base_url = base_url or settings.ollama_base_url

        self._embeddings: OllamaEmbeddings | None = None

    @property
    def embeddings(self) -> OllamaEmbeddings:
        """Lazy-load embeddings client."""
        if self._embeddings is None:
            self._embeddings = OllamaEmbeddings(
                model=self.model,
                base_url=self.base_url,
            )
        return self._embeddings

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            embedding = self.embeddings.embed_query(text)
            logger.debug(
                "Generated embedding",
                text_length=len(text),
                embedding_dim=len(embedding),
            )
            return embedding
        except Exception as e:
            logger.error(
                "Embedding generation failed",
                error=str(e),
                model=self.model,
            )
            raise EmbeddingError(f"Failed to generate embedding: {e}")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            return []

        try:
            embeddings = self.embeddings.embed_documents(texts)
            logger.info(
                "Generated batch embeddings",
                text_count=len(texts),
                embedding_dim=len(embeddings[0]) if embeddings else 0,
            )
            return embeddings
        except Exception as e:
            logger.error(
                "Batch embedding generation failed",
                error=str(e),
                model=self.model,
                text_count=len(texts),
            )
            raise EmbeddingError(f"Failed to generate embeddings: {e}")

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings from this model.

        Returns:
            Embedding dimension
        """
        # Generate a test embedding to determine dimension
        test_embedding = self.embed_text("test")
        return len(test_embedding)


# Singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get the singleton embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
