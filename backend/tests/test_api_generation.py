"""Tests for generation API endpoints."""

import io
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


class TestGenerateDraft:
    """Tests for draft generation endpoint."""

    def test_generate_draft_success(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Should successfully generate a draft."""
        self._reset_singletons()

        mock_llm.set_response(
            "This is generated content with [Source 1] citations. "
            "[Source 2] provides additional context."
        )

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                                with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                                    from app.main import app
                                    client = TestClient(app)

                                    # First upload a document
                                    files = {
                                        "file": ("test.txt", io.BytesIO(b"Source content for generation."), "text/plain")
                                    }
                                    client.post("/api/documents", files=files)

                                    # Patch the LLM
                                    from app.services.generation import GenerationService
                                    original_init = GenerationService.__init__

                                    def patched_init(self):
                                        original_init(self)
                                        self._llm = mock_llm

                                    with patch.object(GenerationService, '__init__', patched_init):
                                        # Generate a draft
                                        response = client.post(
                                            "/api/generate",
                                            json={
                                                "prompt": "Write about the source content",
                                                "max_sections": 3,
                                            }
                                        )

                                        assert response.status_code == 200
                                        result = response.json()

                                        # Verify response structure
                                        assert "generation_id" in result
                                        assert "sections" in result
                                        assert "retrieval_metadata" in result
                                        assert "total_sources_used" in result
                                        assert "generation_time_ms" in result

        self._reset_singletons()

    def test_generate_draft_response_schema(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Response should have correct schema with RAG metadata."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                                with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                                    from app.main import app
                                    client = TestClient(app)

                                    # Upload document
                                    files = {
                                        "file": ("test.txt", io.BytesIO(b"Content for testing."), "text/plain")
                                    }
                                    client.post("/api/documents", files=files)

                                    from app.services.generation import GenerationService
                                    original_init = GenerationService.__init__

                                    def patched_init(self):
                                        original_init(self)
                                        self._llm = mock_llm

                                    with patch.object(GenerationService, '__init__', patched_init):
                                        response = client.post(
                                            "/api/generate",
                                            json={"prompt": "Test prompt"}
                                        )

                                        result = response.json()

                                        # Verify sections have required fields
                                        if result.get("sections"):
                                            section = result["sections"][0]
                                            assert "section_id" in section
                                            assert "content" in section
                                            assert "sources" in section
                                            assert "confidence" in section
                                            assert "warnings" in section

                                            # Sources must be array, never null
                                            assert section["sources"] is not None
                                            assert isinstance(section["sources"], list)

                                        # Verify retrieval metadata
                                        metadata = result.get("retrieval_metadata", {})
                                        assert "query" in metadata
                                        assert "chunks_retrieved" in metadata
                                        assert "retrieval_time_ms" in metadata

        self._reset_singletons()

    def test_generate_empty_prompt_rejected(
        self, mock_settings, mock_embedding_service
    ):
        """Should reject empty prompts."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                            from app.main import app
                            client = TestClient(app)

                            response = client.post(
                                "/api/generate",
                                json={"prompt": ""}
                            )

                            # Should be rejected by validation
                            assert response.status_code == 422

        self._reset_singletons()

    def test_generate_llm_error_503(
        self, mock_settings, mock_embedding_service
    ):
        """LLM errors should return 503 status."""
        self._reset_singletons()

        # Create a failing LLM mock
        failing_llm = MagicMock()
        failing_llm.ainvoke = AsyncMock(side_effect=Exception("Ollama connection refused"))

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                                with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                                    from app.main import app
                                    client = TestClient(app)

                                    # Upload document
                                    files = {
                                        "file": ("test.txt", io.BytesIO(b"Content."), "text/plain")
                                    }
                                    client.post("/api/documents", files=files)

                                    from app.services.generation import GenerationService
                                    original_init = GenerationService.__init__

                                    def patched_init(self):
                                        original_init(self)
                                        self._llm = failing_llm

                                    with patch.object(GenerationService, '__init__', patched_init):
                                        response = client.post(
                                            "/api/generate",
                                            json={"prompt": "Test prompt"}
                                        )

                                        assert response.status_code == 503
                                        assert "LLM" in response.json()["detail"]

        self._reset_singletons()

    def test_generation_response_sources_not_null(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Sources should never be null in response."""
        self._reset_singletons()

        # Response without citations
        mock_llm.set_response("Generated content without any citations.")

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                                with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                                    from app.main import app
                                    client = TestClient(app)

                                    # Upload document
                                    files = {
                                        "file": ("test.txt", io.BytesIO(b"Content."), "text/plain")
                                    }
                                    client.post("/api/documents", files=files)

                                    from app.services.generation import GenerationService
                                    original_init = GenerationService.__init__

                                    def patched_init(self):
                                        original_init(self)
                                        self._llm = mock_llm

                                    with patch.object(GenerationService, '__init__', patched_init):
                                        response = client.post(
                                            "/api/generate",
                                            json={"prompt": "Test prompt"}
                                        )

                                        result = response.json()

                                        # Verify sources are never null
                                        for section in result.get("sections", []):
                                            assert section["sources"] is not None
                                            assert isinstance(section["sources"], list)

        self._reset_singletons()

    def _reset_singletons(self):
        """Reset all singleton instances."""
        import app.services.ingestion as ingestion_module
        import app.services.retrieval as retrieval_module
        import app.services.generation as generation_module
        import app.rag.vectorstore as vectorstore_module
        import app.rag.embedding as embedding_module

        ingestion_module._ingestion_service = None
        retrieval_module._retrieval_service = None
        generation_module._generation_service = None
        vectorstore_module._vector_store = None
        embedding_module._embedding_service = None


class TestRegenerateSection:
    """Tests for section regeneration endpoint."""

    def test_regenerate_section_success(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Should successfully regenerate a section."""
        self._reset_singletons()

        mock_llm.set_response(
            "Regenerated content with [Source 1] improved citations."
        )

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                                with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                                    from app.main import app
                                    client = TestClient(app)

                                    # Upload document
                                    files = {
                                        "file": ("test.txt", io.BytesIO(b"Source content."), "text/plain")
                                    }
                                    client.post("/api/documents", files=files)

                                    from app.services.generation import GenerationService
                                    original_init = GenerationService.__init__

                                    def patched_init(self):
                                        original_init(self)
                                        self._llm = mock_llm

                                    with patch.object(GenerationService, '__init__', patched_init):
                                        response = client.post(
                                            "/api/generate/section",
                                            json={
                                                "section_id": "section-001",
                                                "prompt": "Make it more detailed",
                                            }
                                        )

                                        assert response.status_code == 200
                                        result = response.json()

                                        # Verify response structure
                                        assert "section" in result
                                        assert "retrieval_metadata" in result
                                        assert "generation_time_ms" in result

                                        # Verify section has required fields
                                        section = result["section"]
                                        assert section["section_id"] == "section-001"
                                        assert "content" in section
                                        assert "sources" in section
                                        assert section["sources"] is not None

        self._reset_singletons()

    def _reset_singletons(self):
        """Reset all singleton instances."""
        import app.services.ingestion as ingestion_module
        import app.services.retrieval as retrieval_module
        import app.services.generation as generation_module
        import app.rag.vectorstore as vectorstore_module
        import app.rag.embedding as embedding_module

        ingestion_module._ingestion_service = None
        retrieval_module._retrieval_service = None
        generation_module._generation_service = None
        vectorstore_module._vector_store = None
        embedding_module._embedding_service = None


class TestGenerationMetadata:
    """Tests for generation metadata verification."""

    def test_generation_includes_timing(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Generation should include timing information."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                                with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                                    from app.main import app
                                    client = TestClient(app)

                                    files = {
                                        "file": ("test.txt", io.BytesIO(b"Content."), "text/plain")
                                    }
                                    client.post("/api/documents", files=files)

                                    from app.services.generation import GenerationService
                                    original_init = GenerationService.__init__

                                    def patched_init(self):
                                        original_init(self)
                                        self._llm = mock_llm

                                    with patch.object(GenerationService, '__init__', patched_init):
                                        response = client.post(
                                            "/api/generate",
                                            json={"prompt": "Test"}
                                        )

                                        result = response.json()

                                        # Verify timing is present and positive
                                        assert result["generation_time_ms"] >= 0
                                        assert result["retrieval_metadata"]["retrieval_time_ms"] >= 0

        self._reset_singletons()

    def test_generation_includes_model_used(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Generation should specify which model was used."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                                with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                                    from app.main import app
                                    client = TestClient(app)

                                    files = {
                                        "file": ("test.txt", io.BytesIO(b"Content."), "text/plain")
                                    }
                                    client.post("/api/documents", files=files)

                                    from app.services.generation import GenerationService
                                    original_init = GenerationService.__init__

                                    def patched_init(self):
                                        original_init(self)
                                        self._llm = mock_llm

                                    with patch.object(GenerationService, '__init__', patched_init):
                                        response = client.post(
                                            "/api/generate",
                                            json={"prompt": "Test"}
                                        )

                                        result = response.json()

                                        assert "model_used" in result
                                        assert result["model_used"] is not None

        self._reset_singletons()

    def _reset_singletons(self):
        """Reset all singleton instances."""
        import app.services.ingestion as ingestion_module
        import app.services.retrieval as retrieval_module
        import app.services.generation as generation_module
        import app.rag.vectorstore as vectorstore_module
        import app.rag.embedding as embedding_module

        ingestion_module._ingestion_service = None
        retrieval_module._retrieval_service = None
        generation_module._generation_service = None
        vectorstore_module._vector_store = None
        embedding_module._embedding_service = None


class TestRAGMetadataVerification:
    """Tests to verify RAG metadata is never silently dropped."""

    def test_sources_array_never_null(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Sources should always be an array, never null."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                                with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                                    from app.main import app
                                    client = TestClient(app)

                                    files = {
                                        "file": ("test.txt", io.BytesIO(b"Content."), "text/plain")
                                    }
                                    client.post("/api/documents", files=files)

                                    from app.services.generation import GenerationService
                                    original_init = GenerationService.__init__

                                    def patched_init(self):
                                        original_init(self)
                                        self._llm = mock_llm

                                    with patch.object(GenerationService, '__init__', patched_init):
                                        response = client.post(
                                            "/api/generate",
                                            json={"prompt": "Test"}
                                        )

                                        result = response.json()

                                        for section in result["sections"]:
                                            # Critical: sources must NEVER be null
                                            assert section["sources"] is not None, \
                                                "sources should never be null"
                                            assert isinstance(section["sources"], list), \
                                                "sources should be a list"

        self._reset_singletons()

    def test_confidence_always_present(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Confidence level should always be present."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                                with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                                    from app.main import app
                                    client = TestClient(app)

                                    files = {
                                        "file": ("test.txt", io.BytesIO(b"Content."), "text/plain")
                                    }
                                    client.post("/api/documents", files=files)

                                    from app.services.generation import GenerationService
                                    original_init = GenerationService.__init__

                                    def patched_init(self):
                                        original_init(self)
                                        self._llm = mock_llm

                                    with patch.object(GenerationService, '__init__', patched_init):
                                        response = client.post(
                                            "/api/generate",
                                            json={"prompt": "Test"}
                                        )

                                        result = response.json()

                                        for section in result["sections"]:
                                            assert section["confidence"] is not None
                                            assert section["confidence"] in [
                                                "high", "medium", "low", "unknown"
                                            ]

        self._reset_singletons()

    def test_warnings_array_always_present(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Warnings should always be present as an array."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                                with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                                    from app.main import app
                                    client = TestClient(app)

                                    files = {
                                        "file": ("test.txt", io.BytesIO(b"Content."), "text/plain")
                                    }
                                    client.post("/api/documents", files=files)

                                    from app.services.generation import GenerationService
                                    original_init = GenerationService.__init__

                                    def patched_init(self):
                                        original_init(self)
                                        self._llm = mock_llm

                                    with patch.object(GenerationService, '__init__', patched_init):
                                        response = client.post(
                                            "/api/generate",
                                            json={"prompt": "Test"}
                                        )

                                        result = response.json()

                                        for section in result["sections"]:
                                            assert section["warnings"] is not None
                                            assert isinstance(section["warnings"], list)

        self._reset_singletons()

    def _reset_singletons(self):
        """Reset all singleton instances."""
        import app.services.ingestion as ingestion_module
        import app.services.retrieval as retrieval_module
        import app.services.generation as generation_module
        import app.rag.vectorstore as vectorstore_module
        import app.rag.embedding as embedding_module

        ingestion_module._ingestion_service = None
        retrieval_module._retrieval_service = None
        generation_module._generation_service = None
        vectorstore_module._vector_store = None
        embedding_module._embedding_service = None
