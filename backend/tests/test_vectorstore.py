"""Tests for FAISS vector store."""

from unittest.mock import patch

from app.models import DocumentChunk
from app.rag.vectorstore import VectorStore


class TestVectorStoreBasics:
    """Tests for basic vector store operations."""

    def test_add_chunks_creates_index(self, mock_settings, mock_embedding_service, sample_chunks):
        """Adding chunks should create a FAISS index."""
        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)

                assert store.index is None
                assert len(store.chunks) == 0

                store.add_chunks(sample_chunks)

                assert store.index is not None
                assert len(store.chunks) == len(sample_chunks)

    def test_add_empty_chunks_does_nothing(self, mock_settings, mock_embedding_service):
        """Adding an empty list should not change the store."""
        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)

                store.add_chunks([])

                assert store.index is None
                assert len(store.chunks) == 0

    def test_add_chunks_with_metadata(self, mock_settings, mock_embedding_service):
        """Chunks should preserve their metadata after adding."""
        chunks = [
            DocumentChunk(
                chunk_id="chunk-001",
                document_id="doc-001",
                content="Test content with metadata",
                chunk_index=0,
                start_char=0,
                end_char=25,
                metadata={"title": "Test", "author": "Tester"},
            )
        ]

        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)
                store.add_chunks(chunks)

                assert store.chunks[0].metadata["title"] == "Test"
                assert store.chunks[0].metadata["author"] == "Tester"


class TestVectorStoreSearch:
    """Tests for vector store search functionality."""

    def test_search_returns_similar_chunks(
        self, mock_settings, mock_embedding_service, sample_chunks
    ):
        """Search should return chunks similar to the query."""
        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)
                store.add_chunks(sample_chunks)

                # Search for content related to chunk 0
                results = store.search(
                    query=sample_chunks[0].content,
                    top_k=3,
                    threshold=0.0,  # Low threshold for mock embeddings
                )

                assert len(results) > 0
                assert all(isinstance(r[0], DocumentChunk) for r in results)
                assert all(isinstance(r[1], float) for r in results)

    def test_search_empty_store_returns_empty(self, mock_settings, mock_embedding_service):
        """Searching an empty store should return empty list."""
        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)

                results = store.search(query="test query", top_k=5)

                assert results == []

    def test_search_respects_top_k_limit(
        self, mock_settings, mock_embedding_service, sample_chunks_factory
    ):
        """Search should return at most top_k results."""
        chunks = sample_chunks_factory(count=10)

        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)
                store.add_chunks(chunks)

                results = store.search(
                    query="test content",
                    top_k=3,
                    threshold=0.0,
                )

                assert len(results) <= 3

    def test_search_respects_similarity_threshold(
        self, mock_settings, mock_embedding_service, sample_chunks
    ):
        """Search should filter results below the threshold."""
        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)
                store.add_chunks(sample_chunks)

                # High threshold should filter most results
                results = store.search(
                    query="unrelated query",
                    top_k=10,
                    threshold=0.99,
                )

                # Results should be filtered by threshold
                assert all(r[1] >= 0.99 for r in results)

    def test_search_with_document_filter(self, mock_settings, mock_embedding_service):
        """Search should filter by document IDs when specified."""
        chunks = [
            DocumentChunk(
                chunk_id=f"doc1-chunk-{i}",
                document_id="doc-001",
                content=f"Content from document 1, chunk {i}",
                chunk_index=i,
                start_char=0,
                end_char=50,
            )
            for i in range(3)
        ] + [
            DocumentChunk(
                chunk_id=f"doc2-chunk-{i}",
                document_id="doc-002",
                content=f"Content from document 2, chunk {i}",
                chunk_index=i,
                start_char=0,
                end_char=50,
            )
            for i in range(3)
        ]

        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)
                store.add_chunks(chunks)

                # Filter to only doc-001
                results = store.search(
                    query="Content from document",
                    top_k=10,
                    threshold=0.0,
                    document_ids=["doc-001"],
                )

                assert all(r[0].document_id == "doc-001" for r in results)

    def test_search_results_sorted_by_relevance(
        self, mock_settings, mock_embedding_service, sample_chunks
    ):
        """Search results should be sorted by relevance score (descending)."""
        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)
                store.add_chunks(sample_chunks)

                results = store.search(
                    query="test content",
                    top_k=5,
                    threshold=0.0,
                )

                if len(results) > 1:
                    scores = [r[1] for r in results]
                    # FAISS returns in descending order by default for IndexFlatIP
                    assert scores == sorted(scores, reverse=True)


class TestVectorStoreDelete:
    """Tests for vector store deletion."""

    def test_delete_document_removes_all_chunks(
        self, mock_settings, mock_embedding_service, sample_chunks_factory
    ):
        """Deleting a document should remove all its chunks."""
        doc1_chunks = sample_chunks_factory(document_id="doc-001", count=3)
        doc2_chunks = sample_chunks_factory(document_id="doc-002", count=3)

        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)
                store.add_chunks(doc1_chunks + doc2_chunks)

                assert len(store.chunks) == 6

                deleted_count = store.delete_document("doc-001")

                assert deleted_count == 3
                assert len(store.chunks) == 3
                assert all(c.document_id == "doc-002" for c in store.chunks)

    def test_delete_nonexistent_document(
        self, mock_settings, mock_embedding_service, sample_chunks
    ):
        """Deleting a nonexistent document should return 0."""
        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)
                store.add_chunks(sample_chunks)

                deleted_count = store.delete_document("nonexistent-doc")

                assert deleted_count == 0
                assert len(store.chunks) == len(sample_chunks)

    def test_delete_all_documents_clears_store(
        self, mock_settings, mock_embedding_service, sample_chunks
    ):
        """Deleting the only document should clear the store."""
        # All sample chunks have the same document_id
        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)
                store.add_chunks(sample_chunks)

                store.delete_document("doc-001")

                assert len(store.chunks) == 0
                # Index should be reset when all chunks are deleted
                assert store.index is None


class TestVectorStorePersistence:
    """Tests for vector store persistence."""

    def test_save_and_load(self, mock_settings, mock_embedding_service, sample_chunks):
        """Vector store should persist and reload correctly."""
        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                # Create and populate store
                store1 = VectorStore(store_path=mock_settings.vectors_dir)
                store1.add_chunks(sample_chunks)

                chunk_count = len(store1.chunks)

                # Create new store instance that loads from disk
                store2 = VectorStore(store_path=mock_settings.vectors_dir)

                assert len(store2.chunks) == chunk_count
                assert store2.index is not None

    def test_persistence_preserves_chunk_data(self, mock_settings, mock_embedding_service):
        """Persisted chunks should preserve all their data."""
        original_chunk = DocumentChunk(
            chunk_id="test-chunk-001",
            document_id="test-doc-001",
            content="Test content for persistence",
            chunk_index=0,
            start_char=0,
            end_char=29,
            page_number=1,
            section_title="Test Section",
            metadata={"title": "Test", "author": "Tester"},
        )

        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store1 = VectorStore(store_path=mock_settings.vectors_dir)
                store1.add_chunks([original_chunk])

                store2 = VectorStore(store_path=mock_settings.vectors_dir)

                loaded_chunk = store2.chunks[0]
                assert loaded_chunk.chunk_id == original_chunk.chunk_id
                assert loaded_chunk.document_id == original_chunk.document_id
                assert loaded_chunk.content == original_chunk.content
                assert loaded_chunk.page_number == original_chunk.page_number
                assert loaded_chunk.metadata == original_chunk.metadata


class TestVectorStoreStats:
    """Tests for vector store statistics."""

    def test_get_stats_empty_store(self, mock_settings, mock_embedding_service):
        """Stats for empty store should show zeros."""
        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)

                stats = store.get_stats()

                assert stats["total_chunks"] == 0
                assert stats["total_documents"] == 0
                assert stats["index_trained"] is False

    def test_get_stats_populated_store(
        self, mock_settings, mock_embedding_service, sample_chunks_factory
    ):
        """Stats should reflect the store contents."""
        doc1_chunks = sample_chunks_factory(document_id="doc-001", count=3)
        doc2_chunks = sample_chunks_factory(document_id="doc-002", count=5)

        with patch(
            "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
        ):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                store = VectorStore(store_path=mock_settings.vectors_dir)
                store.add_chunks(doc1_chunks + doc2_chunks)

                stats = store.get_stats()

                assert stats["total_chunks"] == 8
                assert stats["total_documents"] == 2
                assert stats["index_trained"] is True
