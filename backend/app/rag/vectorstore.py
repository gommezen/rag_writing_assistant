"""FAISS vector store abstraction with metadata support.

Provides a clean interface for storing and retrieving document chunks
with their embeddings and metadata.
"""

import pickle
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from ..config import get_settings
from ..core import VectorStoreError, get_logger
from ..models import DocumentChunk
from .embedding import get_embedding_service

logger = get_logger(__name__)


class VectorStore:
    """FAISS-based vector store with metadata support."""

    def __init__(self, store_path: Path | None = None):
        """Initialize vector store.

        Args:
            store_path: Path to store index and metadata. Defaults to settings value.
        """
        settings = get_settings()
        self.store_path = store_path or settings.vectors_dir

        self.index: faiss.IndexFlatIP | None = None
        self.chunks: list[DocumentChunk] = []
        self.embedding_service = get_embedding_service()
        self._stored_embedding_model: str | None = None  # Model used for stored embeddings

        self._index_path = self.store_path / "index.faiss"
        self._metadata_path = self.store_path / "metadata.pkl"
        self._model_path = self.store_path / "embedding_model.txt"

        # Load existing index if available
        self._load()

    def _load(self) -> None:
        """Load existing index and metadata from disk."""
        if self._index_path.exists() and self._metadata_path.exists():
            try:
                self.index = faiss.read_index(str(self._index_path))
                with open(self._metadata_path, "rb") as f:
                    self.chunks = pickle.load(f)

                # Load stored embedding model if available
                if self._model_path.exists():
                    with open(self._model_path) as f:
                        self._stored_embedding_model = f.read().strip()

                # Warn if embedding model has changed
                current_model = self.embedding_service.model
                if self._stored_embedding_model and self._stored_embedding_model != current_model:
                    logger.warning(
                        "Embedding model mismatch - consider running migration",
                        stored_model=self._stored_embedding_model,
                        current_model=current_model,
                    )

                logger.info(
                    "Loaded vector store",
                    chunk_count=len(self.chunks),
                    embedding_model=self._stored_embedding_model or "unknown",
                )
            except Exception as e:
                logger.warning(
                    "Failed to load vector store, starting fresh",
                    error=str(e),
                )
                self.index = None
                self.chunks = []

    def _save(self) -> None:
        """Save index and metadata to disk."""
        if self.index is None:
            return

        try:
            self.store_path.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(self._index_path))
            with open(self._metadata_path, "wb") as f:
                pickle.dump(self.chunks, f)

            # Store embedding model for future compatibility checking
            with open(self._model_path, "w") as f:
                f.write(self.embedding_service.model)
            self._stored_embedding_model = self.embedding_service.model

            logger.info(
                "Saved vector store",
                chunk_count=len(self.chunks),
                embedding_model=self.embedding_service.model,
            )
        except Exception as e:
            logger.error("Failed to save vector store", error=str(e))
            raise VectorStoreError(f"Failed to save vector store: {e}")

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Add document chunks to the vector store.

        Args:
            chunks: List of document chunks to add

        Raises:
            VectorStoreError: If adding chunks fails
        """
        if not chunks:
            return

        try:
            # Generate embeddings for all chunks
            texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_service.embed_texts(texts)

            # Convert to numpy array and normalize for cosine similarity
            vectors = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(vectors)

            # Initialize index if needed
            if self.index is None:
                dimension = vectors.shape[1]
                self.index = faiss.IndexFlatIP(dimension)

            # Add vectors to index
            self.index.add(vectors)
            self.chunks.extend(chunks)

            # Save to disk
            self._save()

            logger.info(
                "Added chunks to vector store",
                new_chunks=len(chunks),
                total_chunks=len(self.chunks),
            )

        except Exception as e:
            logger.error("Failed to add chunks to vector store", error=str(e))
            raise VectorStoreError(f"Failed to add chunks: {e}")

    def search(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
        document_ids: list[str] | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """Search for similar chunks.

        Args:
            query: Query text to search for
            top_k: Number of results to return. Defaults to settings value.
            threshold: Minimum similarity threshold. Defaults to settings value.
            document_ids: Optional list of document IDs to filter by

        Returns:
            List of (chunk, similarity_score) tuples sorted by relevance

        Raises:
            VectorStoreError: If search fails
        """
        settings = get_settings()
        top_k = top_k or settings.top_k_retrieval
        threshold = threshold if threshold is not None else settings.similarity_threshold

        if self.index is None or len(self.chunks) == 0:
            logger.warning("Search attempted on empty vector store")
            return []

        try:
            # Generate query embedding
            query_embedding = self.embedding_service.embed_text(query)
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)

            # Search index
            # Request more results if filtering by document_ids
            search_k = top_k * 3 if document_ids else top_k
            search_k = min(search_k, len(self.chunks))

            scores, indices = self.index.search(query_vector, search_k)

            # Build results with filtering
            results: list[tuple[DocumentChunk, float]] = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0:  # FAISS returns -1 for empty slots
                    continue

                chunk = self.chunks[idx]

                # Filter by document IDs if specified
                if document_ids and chunk.document_id not in document_ids:
                    continue

                # Filter by threshold
                if score < threshold:
                    continue

                results.append((chunk, float(score)))

                if len(results) >= top_k:
                    break

            logger.info(
                "Vector search completed",
                query_length=len(query),
                results_found=len(results),
                top_k=top_k,
                threshold=threshold,
            )

            return results

        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            raise VectorStoreError(f"Search failed: {e}")

    def delete_document(self, document_id: str) -> int:
        """Delete all chunks for a document.

        Note: FAISS doesn't support deletion efficiently, so we rebuild the index.

        Args:
            document_id: ID of document to delete

        Returns:
            Number of chunks deleted
        """
        # Find chunks to keep
        remaining_chunks = [c for c in self.chunks if c.document_id != document_id]
        deleted_count = len(self.chunks) - len(remaining_chunks)

        if deleted_count == 0:
            return 0

        # Reset and rebuild
        self.chunks = []
        self.index = None

        if remaining_chunks:
            self.add_chunks(remaining_chunks)
        else:
            # Clear stored files if no chunks remain
            if self._index_path.exists():
                self._index_path.unlink()
            if self._metadata_path.exists():
                self._metadata_path.unlink()

        logger.info(
            "Deleted document from vector store",
            document_id=document_id,
            chunks_deleted=deleted_count,
        )

        return deleted_count

    def get_stats(self) -> dict[str, Any]:
        """Get vector store statistics."""
        document_ids = set(c.document_id for c in self.chunks)
        return {
            "total_chunks": len(self.chunks),
            "total_documents": len(document_ids),
            "index_trained": self.index is not None,
            "embedding_model": self._stored_embedding_model or self.embedding_service.model,
        }


# Singleton instance
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Get the singleton vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
