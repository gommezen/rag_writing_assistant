"""Tests for retrieval service."""

from datetime import datetime
from unittest.mock import patch

from app.models import DocumentChunk, RetrievalMetadata, SourceReference
from app.services.retrieval import RetrievalService


class TestRetrievalServiceBasics:
    """Tests for basic retrieval functionality."""

    def test_retrieve_returns_sources_with_metadata(
        self, mock_settings, mock_embedding_service, sample_chunks_factory
    ):
        """Retrieval should return SourceReferences with complete metadata."""
        chunks = sample_chunks_factory(
            document_id="doc-001",
            count=5,
            metadata={"title": "Test Document", "author": "Test Author"},
        )

        with patch("app.services.retrieval.get_settings", return_value=mock_settings):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                with patch(
                    "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
                ):
                    # Set up vector store with chunks
                    from app.rag.vectorstore import VectorStore

                    vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                    vector_store.add_chunks(chunks)

                    with patch(
                        "app.services.retrieval.get_vector_store", return_value=vector_store
                    ):
                        service = RetrievalService()

                        sources, metadata = service.retrieve(
                            query="Test content",
                            top_k=3,
                            threshold=0.0,
                        )

                        # Verify sources are returned
                        assert len(sources) > 0
                        assert all(isinstance(s, SourceReference) for s in sources)

                        # Verify each source has required fields
                        for source in sources:
                            assert source.document_id is not None
                            assert source.chunk_id is not None
                            assert source.excerpt is not None
                            assert isinstance(source.relevance_score, float)
                            assert source.metadata is not None

                        # Verify metadata is returned
                        assert isinstance(metadata, RetrievalMetadata)
                        assert metadata.query == "Test content"
                        assert metadata.top_k == 3
                        assert metadata.retrieval_time_ms >= 0

    def test_retrieve_respects_similarity_threshold(
        self, mock_settings, mock_embedding_service, sample_chunks_factory
    ):
        """Only sources above threshold should be returned."""
        chunks = sample_chunks_factory(count=5)

        with patch("app.services.retrieval.get_settings", return_value=mock_settings):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                with patch(
                    "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
                ):
                    from app.rag.vectorstore import VectorStore

                    vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                    vector_store.add_chunks(chunks)

                    with patch(
                        "app.services.retrieval.get_vector_store", return_value=vector_store
                    ):
                        service = RetrievalService()

                        sources, metadata = service.retrieve(
                            query="Test query",
                            top_k=10,
                            threshold=0.8,
                        )

                        # All returned sources should be above threshold
                        for source in sources:
                            assert source.relevance_score >= 0.8

                        assert metadata.similarity_threshold == 0.8

    def test_retrieve_respects_top_k_limit(
        self, mock_settings, mock_embedding_service, sample_chunks_factory
    ):
        """Should return at most top_k sources."""
        chunks = sample_chunks_factory(count=20)

        with patch("app.services.retrieval.get_settings", return_value=mock_settings):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                with patch(
                    "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
                ):
                    from app.rag.vectorstore import VectorStore

                    vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                    vector_store.add_chunks(chunks)

                    with patch(
                        "app.services.retrieval.get_vector_store", return_value=vector_store
                    ):
                        service = RetrievalService()

                        sources, metadata = service.retrieve(
                            query="Test query",
                            top_k=5,
                            threshold=0.0,
                        )

                        assert len(sources) <= 5
                        assert metadata.top_k == 5

    def test_empty_vector_store_returns_empty(self, mock_settings, mock_embedding_service):
        """Searching an empty store should return empty results."""
        with patch("app.services.retrieval.get_settings", return_value=mock_settings):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                with patch(
                    "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
                ):
                    from app.rag.vectorstore import VectorStore

                    vector_store = VectorStore(store_path=mock_settings.vectors_dir)

                    with patch(
                        "app.services.retrieval.get_vector_store", return_value=vector_store
                    ):
                        service = RetrievalService()

                        sources, metadata = service.retrieve(query="Test query")

                        assert sources == []
                        assert metadata.chunks_retrieved == 0


class TestRetrievalServiceFiltering:
    """Tests for retrieval filtering functionality."""

    def test_retrieve_with_document_filter(
        self, mock_settings, mock_embedding_service, sample_chunks_factory
    ):
        """Should filter results by document IDs."""
        doc1_chunks = sample_chunks_factory(document_id="doc-001", count=5)
        doc2_chunks = sample_chunks_factory(document_id="doc-002", count=5)

        with patch("app.services.retrieval.get_settings", return_value=mock_settings):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                with patch(
                    "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
                ):
                    from app.rag.vectorstore import VectorStore

                    vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                    vector_store.add_chunks(doc1_chunks + doc2_chunks)

                    with patch(
                        "app.services.retrieval.get_vector_store", return_value=vector_store
                    ):
                        service = RetrievalService()

                        sources, _ = service.retrieve(
                            query="Test content",
                            top_k=10,
                            threshold=0.0,
                            document_ids=["doc-001"],
                        )

                        # All sources should be from doc-001
                        for source in sources:
                            assert source.document_id == "doc-001"

    def test_retrieve_with_multiple_document_filters(
        self, mock_settings, mock_embedding_service, sample_chunks_factory
    ):
        """Should filter by multiple document IDs."""
        doc1_chunks = sample_chunks_factory(document_id="doc-001", count=3)
        doc2_chunks = sample_chunks_factory(document_id="doc-002", count=3)
        doc3_chunks = sample_chunks_factory(document_id="doc-003", count=3)

        with patch("app.services.retrieval.get_settings", return_value=mock_settings):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                with patch(
                    "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
                ):
                    from app.rag.vectorstore import VectorStore

                    vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                    vector_store.add_chunks(doc1_chunks + doc2_chunks + doc3_chunks)

                    with patch(
                        "app.services.retrieval.get_vector_store", return_value=vector_store
                    ):
                        service = RetrievalService()

                        sources, _ = service.retrieve(
                            query="Test content",
                            top_k=10,
                            threshold=0.0,
                            document_ids=["doc-001", "doc-003"],
                        )

                        # All sources should be from doc-001 or doc-003
                        for source in sources:
                            assert source.document_id in ["doc-001", "doc-003"]


class TestRetrievalMetadata:
    """Tests for retrieval metadata tracking."""

    def test_retrieval_metadata_tracked(
        self, mock_settings, mock_embedding_service, sample_chunks_factory
    ):
        """Retrieval metadata should include all required fields."""
        chunks = sample_chunks_factory(count=5)

        with patch("app.services.retrieval.get_settings", return_value=mock_settings):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                with patch(
                    "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
                ):
                    from app.rag.vectorstore import VectorStore

                    vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                    vector_store.add_chunks(chunks)

                    with patch(
                        "app.services.retrieval.get_vector_store", return_value=vector_store
                    ):
                        service = RetrievalService()

                        _, metadata = service.retrieve(
                            query="Test query for metadata",
                            top_k=3,
                            threshold=0.5,
                        )

                        # Verify all metadata fields
                        assert metadata.query == "Test query for metadata"
                        assert metadata.top_k == 3
                        assert metadata.similarity_threshold == 0.5
                        assert metadata.chunks_retrieved >= 0
                        assert metadata.chunks_above_threshold >= 0
                        assert metadata.retrieval_time_ms >= 0
                        assert isinstance(metadata.timestamp, datetime)

    def test_retrieval_tracks_timing(
        self, mock_settings, mock_embedding_service, sample_chunks_factory
    ):
        """Retrieval should track timing information."""
        chunks = sample_chunks_factory(count=10)

        with patch("app.services.retrieval.get_settings", return_value=mock_settings):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                with patch(
                    "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
                ):
                    from app.rag.vectorstore import VectorStore

                    vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                    vector_store.add_chunks(chunks)

                    with patch(
                        "app.services.retrieval.get_vector_store", return_value=vector_store
                    ):
                        service = RetrievalService()

                        _, metadata = service.retrieve(query="Test query")

                        # Timing should be a non-negative number (can be 0 for fast operations)
                        assert metadata.retrieval_time_ms >= 0


class TestRetrievalExcerpts:
    """Tests for excerpt handling."""

    def test_excerpt_truncation(self, mock_settings, mock_embedding_service):
        """Long content should be truncated in excerpts."""
        long_content = "A" * 500  # 500 character content
        chunks = [
            DocumentChunk(
                chunk_id="long-chunk",
                document_id="doc-001",
                content=long_content,
                chunk_index=0,
                start_char=0,
                end_char=500,
            )
        ]

        with patch("app.services.retrieval.get_settings", return_value=mock_settings):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                with patch(
                    "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
                ):
                    from app.rag.vectorstore import VectorStore

                    vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                    vector_store.add_chunks(chunks)

                    with patch(
                        "app.services.retrieval.get_vector_store", return_value=vector_store
                    ):
                        service = RetrievalService()

                        sources, _ = service.retrieve(
                            query="A" * 10,
                            top_k=1,
                            threshold=0.0,
                        )

                        # Excerpt should be truncated
                        if sources:
                            assert len(sources[0].excerpt) <= 203  # 200 + "..."

    def test_short_content_not_truncated(self, mock_settings, mock_embedding_service):
        """Short content should not be truncated."""
        short_content = "Short content"
        chunks = [
            DocumentChunk(
                chunk_id="short-chunk",
                document_id="doc-001",
                content=short_content,
                chunk_index=0,
                start_char=0,
                end_char=len(short_content),
            )
        ]

        with patch("app.services.retrieval.get_settings", return_value=mock_settings):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                with patch(
                    "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
                ):
                    from app.rag.vectorstore import VectorStore

                    vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                    vector_store.add_chunks(chunks)

                    with patch(
                        "app.services.retrieval.get_vector_store", return_value=vector_store
                    ):
                        service = RetrievalService()

                        sources, _ = service.retrieve(
                            query="Short",
                            top_k=1,
                            threshold=0.0,
                        )

                        if sources:
                            assert sources[0].excerpt == short_content


class TestRetrievalForSources:
    """Tests for retrieve_for_sources method."""

    def test_retrieve_for_sources_returns_formatted_dict(
        self, mock_settings, mock_embedding_service, sample_chunks_factory
    ):
        """retrieve_for_sources should return properly formatted dicts."""
        chunks = sample_chunks_factory(count=5, metadata={"title": "Test Doc"})

        with patch("app.services.retrieval.get_settings", return_value=mock_settings):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                with patch(
                    "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
                ):
                    from app.rag.vectorstore import VectorStore

                    vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                    vector_store.add_chunks(chunks)

                    with patch(
                        "app.services.retrieval.get_vector_store", return_value=vector_store
                    ):
                        service = RetrievalService()

                        results = service.retrieve_for_sources(
                            query="Test query",
                        )

                        for result in results:
                            assert "content" in result
                            assert "metadata" in result
                            assert isinstance(result["content"], str)
                            assert isinstance(result["metadata"], dict)
