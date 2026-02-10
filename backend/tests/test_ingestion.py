"""Tests for document ingestion service."""

import io
from unittest.mock import patch

import pytest
from app.core import DocumentProcessingError, UnsupportedDocumentTypeError
from app.models import DocumentStatus, DocumentType
from app.services.ingestion import IngestionService


class TestIngestionServiceBasics:
    """Tests for basic ingestion service functionality."""

    @pytest.mark.asyncio
    async def test_ingest_txt_document(self, mock_settings, mock_embedding_service):
        """Should successfully ingest a TXT document."""
        content = b"This is test content.\n\nAnother paragraph here."
        file = io.BytesIO(content)

        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        document = await service.ingest_document(
                            file=file,
                            filename="test_document.txt",
                            metadata={"author": "Test Author"},
                        )

                        assert document is not None
                        assert document.document_type == DocumentType.TXT
                        assert document.status == DocumentStatus.READY
                        assert document.chunk_count > 0
                        assert document.metadata.word_count > 0

    @pytest.mark.asyncio
    async def test_ingest_pdf_document(self, mock_settings, mock_embedding_service, tmp_path):
        """Should successfully ingest a PDF document."""
        # Create a simple PDF using reportlab if available, or use a mock
        pdf_content = self._create_minimal_pdf()

        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        # Use a mock that returns text from "PDF"
                        with patch.object(
                            service, "_parse_pdf", return_value="PDF content for testing"
                        ):
                            file = io.BytesIO(pdf_content)
                            document = await service.ingest_document(
                                file=file,
                                filename="test_document.pdf",
                            )

                            assert document.document_type == DocumentType.PDF
                            assert document.status == DocumentStatus.READY

    def _create_minimal_pdf(self) -> bytes:
        """Create minimal PDF bytes for testing."""
        return b"%PDF-1.4\n%%EOF"

    @pytest.mark.asyncio
    async def test_ingest_docx_document(self, mock_settings, mock_embedding_service):
        """Should successfully ingest a DOCX document."""
        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        # Mock the DOCX parser since we don't have a real DOCX file
                        with patch.object(
                            service, "_parse_docx", return_value="DOCX content for testing"
                        ):
                            file = io.BytesIO(b"fake docx content")
                            document = await service.ingest_document(
                                file=file,
                                filename="test_document.docx",
                            )

                            assert document.document_type == DocumentType.DOCX
                            assert document.status == DocumentStatus.READY


class TestIngestionServiceErrors:
    """Tests for error handling in ingestion service."""

    @pytest.mark.asyncio
    async def test_unsupported_file_type_raises_error(self, mock_settings, mock_embedding_service):
        """Should raise error for unsupported file types."""
        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()
                        file = io.BytesIO(b"some content")

                        with pytest.raises(UnsupportedDocumentTypeError):
                            await service.ingest_document(
                                file=file,
                                filename="test_document.xyz",
                            )

    @pytest.mark.asyncio
    async def test_empty_file_handling(self, mock_settings, mock_embedding_service):
        """Should handle empty files gracefully."""
        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()
                        file = io.BytesIO(b"")

                        document = await service.ingest_document(
                            file=file,
                            filename="empty.txt",
                        )

                        # Empty file should still process but produce 0 chunks
                        assert document.status == DocumentStatus.READY
                        assert document.chunk_count == 0

    @pytest.mark.asyncio
    async def test_corrupted_pdf_handling(self, mock_settings, mock_embedding_service):
        """Should handle corrupted PDF files."""
        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        # Make _parse_pdf raise an exception
                        with patch.object(
                            service,
                            "_parse_pdf",
                            side_effect=Exception("PDF parsing failed"),
                        ):
                            file = io.BytesIO(b"not a real pdf")

                            with pytest.raises(DocumentProcessingError):
                                await service.ingest_document(
                                    file=file,
                                    filename="corrupted.pdf",
                                )


class TestIngestionServiceMetadata:
    """Tests for metadata handling in ingestion."""

    @pytest.mark.asyncio
    async def test_document_metadata_preserved(self, mock_settings, mock_embedding_service):
        """Custom metadata should be preserved in the document."""
        content = b"Test content for metadata test."
        file = io.BytesIO(content)

        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        document = await service.ingest_document(
                            file=file,
                            filename="metadata_test.txt",
                            metadata={
                                "author": "Test Author",
                                "category": "Testing",
                                "version": "1.0",
                            },
                        )

                        assert document.metadata.custom_metadata["author"] == "Test Author"
                        assert document.metadata.custom_metadata["category"] == "Testing"
                        assert document.metadata.custom_metadata["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_title_extracted_from_filename(self, mock_settings, mock_embedding_service):
        """Document title should be extracted from filename if not provided."""
        content = b"Test content."
        file = io.BytesIO(content)

        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        document = await service.ingest_document(
                            file=file,
                            filename="my_important_document.txt",
                        )

                        # Title should be the filename without extension
                        assert document.metadata.title == "my_important_document"

    @pytest.mark.asyncio
    async def test_word_count_calculated(self, mock_settings, mock_embedding_service):
        """Word count should be calculated from content."""
        content = b"One two three four five six seven eight nine ten."
        file = io.BytesIO(content)

        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        document = await service.ingest_document(
                            file=file,
                            filename="word_count_test.txt",
                        )

                        assert document.metadata.word_count == 10


class TestIngestionServiceDocumentManagement:
    """Tests for document CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_document_by_id(self, mock_settings, mock_embedding_service):
        """Should retrieve a document by ID."""
        content = b"Test content."
        file = io.BytesIO(content)

        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        document = await service.ingest_document(
                            file=file,
                            filename="test.txt",
                        )

                        retrieved = service.get_document(document.document_id)

                        assert retrieved is not None
                        assert retrieved.document_id == document.document_id

    def test_get_nonexistent_document_returns_none(self, mock_settings, mock_embedding_service):
        """Should return None for nonexistent document ID."""
        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        result = service.get_document("nonexistent-id")

                        assert result is None

    @pytest.mark.asyncio
    async def test_list_documents(self, mock_settings, mock_embedding_service):
        """Should list all documents."""
        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        # Ingest multiple documents
                        for i in range(3):
                            file = io.BytesIO(f"Content {i}".encode())
                            await service.ingest_document(
                                file=file,
                                filename=f"document_{i}.txt",
                            )

                        documents = service.list_documents()

                        assert len(documents) == 3

    @pytest.mark.asyncio
    async def test_delete_document_removes_chunks(self, mock_settings, mock_embedding_service):
        """Deleting a document should remove it and its chunks."""
        content = b"Test content with enough text for chunking."
        file = io.BytesIO(content)

        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        document = await service.ingest_document(
                            file=file,
                            filename="to_delete.txt",
                        )

                        doc_id = document.document_id

                        # Delete the document
                        result = service.delete_document(doc_id)

                        assert result is True
                        assert service.get_document(doc_id) is None

                        # Verify chunks are removed from vector store
                        assert all(c.document_id != doc_id for c in service.vector_store.chunks)

    def test_delete_nonexistent_document(self, mock_settings, mock_embedding_service):
        """Should return False when deleting nonexistent document."""
        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        result = service.delete_document("nonexistent-id")

                        assert result is False


class TestIngestionServiceParsers:
    """Tests for document parsers."""

    def test_parse_txt_simple(self, mock_settings, mock_embedding_service):
        """Should parse simple text files."""
        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        content = b"Simple text content here."
                        file = io.BytesIO(content)

                        result = service._parse_txt(file)

                        assert result == "Simple text content here."

    def test_parse_txt_unicode(self, mock_settings, mock_embedding_service):
        """Should handle Unicode content."""
        with patch("app.services.ingestion.get_settings", return_value=mock_settings):
            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        service = IngestionService()

                        content = "Unicode: café, naïve, résumé".encode()
                        file = io.BytesIO(content)

                        result = service._parse_txt(file)

                        assert "café" in result
                        assert "naïve" in result
