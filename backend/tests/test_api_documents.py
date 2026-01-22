"""Tests for documents API endpoints."""

import io
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.models import Document, DocumentMetadata, DocumentStatus, DocumentType


class TestDocumentUpload:
    """Tests for document upload endpoint."""

    def test_upload_document_success(self, mock_settings, mock_embedding_service):
        """Should successfully upload a TXT document."""
        # Reset singletons
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                            from app.main import app
                            client = TestClient(app)

                            content = b"Test document content for upload testing."
                            files = {
                                "file": ("test_document.txt", io.BytesIO(content), "text/plain")
                            }
                            data = {
                                "title": "Test Document",
                                "author": "Test Author",
                            }

                            response = client.post(
                                "/api/documents",
                                files=files,
                                data=data,
                            )

                            assert response.status_code == 200
                            result = response.json()

                            assert "document_id" in result
                            assert result["filename"] == "test_document.txt"
                            assert result["document_type"] == "txt"
                            assert result["status"] == "ready"

        self._reset_singletons()

    def test_upload_unsupported_type(self, mock_settings, mock_embedding_service):
        """Should reject unsupported file types."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                            from app.main import app
                            client = TestClient(app)

                            files = {
                                "file": ("test.xyz", io.BytesIO(b"content"), "application/octet-stream")
                            }

                            response = client.post("/api/documents", files=files)

                            assert response.status_code == 400
                            assert "unsupported" in response.json()["detail"].lower()

        self._reset_singletons()

    def test_upload_missing_filename(self, mock_settings, mock_embedding_service):
        """Should handle missing filename gracefully."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                            from app.main import app
                            client = TestClient(app)

                            # Upload without file
                            response = client.post("/api/documents")

                            # FastAPI will return 422 for missing required fields
                            assert response.status_code == 422

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


class TestDocumentList:
    """Tests for document listing endpoint."""

    def test_list_documents(self, mock_settings, mock_embedding_service):
        """Should list all uploaded documents."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                            from app.main import app
                            client = TestClient(app)

                            # Upload some documents first
                            for i in range(3):
                                files = {
                                    "file": (f"doc_{i}.txt", io.BytesIO(f"Content {i}".encode()), "text/plain")
                                }
                                client.post("/api/documents", files=files)

                            # List documents
                            response = client.get("/api/documents")

                            assert response.status_code == 200
                            result = response.json()

                            assert "documents" in result
                            assert "total" in result
                            assert result["total"] >= 3

        self._reset_singletons()

    def test_list_documents_empty(self, mock_settings, mock_embedding_service):
        """Should return empty list when no documents exist."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                            from app.main import app
                            client = TestClient(app)

                            response = client.get("/api/documents")

                            assert response.status_code == 200
                            result = response.json()

                            assert result["documents"] == []
                            assert result["total"] == 0

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


class TestDocumentGet:
    """Tests for getting a single document."""

    def test_get_document_by_id(self, mock_settings, mock_embedding_service):
        """Should retrieve a document by ID."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                            from app.main import app
                            client = TestClient(app)

                            # Upload a document
                            files = {
                                "file": ("test.txt", io.BytesIO(b"Test content"), "text/plain")
                            }
                            upload_response = client.post("/api/documents", files=files)
                            doc_id = upload_response.json()["document_id"]

                            # Get the document
                            response = client.get(f"/api/documents/{doc_id}")

                            assert response.status_code == 200
                            result = response.json()

                            assert result["document_id"] == doc_id
                            assert result["filename"] == "test.txt"

        self._reset_singletons()

    def test_get_document_not_found(self, mock_settings, mock_embedding_service):
        """Should return 404 for nonexistent document."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                            from app.main import app
                            client = TestClient(app)

                            response = client.get("/api/documents/nonexistent-id")

                            assert response.status_code == 404
                            assert "not found" in response.json()["detail"].lower()

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


class TestDocumentDelete:
    """Tests for document deletion endpoint."""

    def test_delete_document_success(self, mock_settings, mock_embedding_service):
        """Should successfully delete a document."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                            from app.main import app
                            client = TestClient(app)

                            # Upload a document
                            files = {
                                "file": ("test.txt", io.BytesIO(b"Test content"), "text/plain")
                            }
                            upload_response = client.post("/api/documents", files=files)
                            doc_id = upload_response.json()["document_id"]

                            # Delete the document
                            response = client.delete(f"/api/documents/{doc_id}")

                            assert response.status_code == 200
                            assert response.json()["status"] == "deleted"

                            # Verify it's gone
                            get_response = client.get(f"/api/documents/{doc_id}")
                            assert get_response.status_code == 404

        self._reset_singletons()

    def test_delete_document_not_found(self, mock_settings, mock_embedding_service):
        """Should return 404 for nonexistent document."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                            from app.main import app
                            client = TestClient(app)

                            response = client.delete("/api/documents/nonexistent-id")

                            assert response.status_code == 404

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


class TestDocumentResponseSchema:
    """Tests to verify response schema compliance."""

    def test_document_response_has_required_fields(self, mock_settings, mock_embedding_service):
        """Document response should have all required fields."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                            from app.main import app
                            client = TestClient(app)

                            files = {
                                "file": ("test.txt", io.BytesIO(b"Content"), "text/plain")
                            }
                            response = client.post("/api/documents", files=files)
                            result = response.json()

                            # Verify all required fields
                            required_fields = [
                                "document_id",
                                "filename",
                                "document_type",
                                "status",
                                "metadata",
                                "chunk_count",
                                "created_at",
                                "updated_at",
                            ]

                            for field in required_fields:
                                assert field in result, f"Missing field: {field}"

        self._reset_singletons()

    def test_metadata_has_required_fields(self, mock_settings, mock_embedding_service):
        """Document metadata should have required fields."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
                            from app.main import app
                            client = TestClient(app)

                            files = {
                                "file": ("test.txt", io.BytesIO(b"Content"), "text/plain")
                            }
                            response = client.post("/api/documents", files=files)
                            metadata = response.json()["metadata"]

                            # Verify metadata structure
                            assert "title" in metadata
                            assert metadata["title"] is not None

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
