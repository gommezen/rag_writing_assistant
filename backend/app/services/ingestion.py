"""Document ingestion service.

Handles document upload, parsing, chunking, and indexing.
"""

import asyncio
import io
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

import httpx
from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader

from ..config import get_settings
from ..core import (
    DocumentProcessingError,
    UnsupportedDocumentTypeError,
    get_logger,
)
from ..models import (
    Document,
    DocumentChunk,
    DocumentMetadata,
    DocumentStatus,
    DocumentType,
)
from ..rag import create_chunker, get_vector_store

logger = get_logger(__name__)

# Thread pool for blocking I/O operations
_executor = ThreadPoolExecutor(max_workers=8)


class IngestionService:
    """Service for ingesting and indexing documents."""

    SUPPORTED_TYPES = {
        ".pdf": DocumentType.PDF,
        ".docx": DocumentType.DOCX,
        ".txt": DocumentType.TXT,
    }

    def __init__(self):
        """Initialize ingestion service."""
        self.settings = get_settings()
        self.chunker = create_chunker()
        self.vector_store = get_vector_store()
        self._documents: dict[str, Document] = {}
        self._load_document_registry()

    def _load_document_registry(self) -> None:
        """Load document registry from disk."""
        registry_path = self.settings.documents_dir / "registry.json"
        if registry_path.exists():
            try:
                with open(registry_path) as f:
                    data = json.load(f)
                    for doc_data in data:
                        doc = Document.from_dict(doc_data)
                        self._documents[doc.document_id] = doc
                logger.info(
                    "Loaded document registry",
                    document_count=len(self._documents),
                )
                # Clean up stale documents that were left processing
                self._cleanup_stale_documents()
            except Exception as e:
                logger.warning("Failed to load document registry", error=str(e))

    def _cleanup_stale_documents(self) -> None:
        """Mark documents stuck in PROCESSING or PENDING state as FAILED.

        This handles cases where the server was restarted during processing.
        """
        stale_count = 0
        for doc in self._documents.values():
            if doc.status in (DocumentStatus.PROCESSING, DocumentStatus.PENDING):
                doc.status = DocumentStatus.FAILED
                doc.error_message = "Processing interrupted by server restart"
                doc.updated_at = datetime.now(UTC)
                stale_count += 1
                logger.warning(
                    "Marked stale document as failed",
                    document_id=doc.document_id,
                    previous_status=doc.status.value,
                )
        if stale_count > 0:
            self._save_document_registry()
            logger.info("Cleaned up stale documents", count=stale_count)

    def _save_document_registry(self) -> None:
        """Save document registry to disk."""
        registry_path = self.settings.documents_dir / "registry.json"
        try:
            self.settings.documents_dir.mkdir(parents=True, exist_ok=True)
            with open(registry_path, "w") as f:
                data = [doc.to_dict() for doc in self._documents.values()]
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save document registry", error=str(e))

    def create_document_record(
        self,
        filename: str,
        metadata: dict[str, str] | None = None,
    ) -> Document:
        """Create a document record without processing.

        This is the fast path for non-blocking uploads. The document
        is created with PENDING status and returned immediately.

        Args:
            filename: Original filename
            metadata: Optional custom metadata

        Returns:
            Document object with PENDING status

        Raises:
            UnsupportedDocumentTypeError: If file type is not supported
        """
        # Validate file type
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.SUPPORTED_TYPES:
            raise UnsupportedDocumentTypeError(
                file_ext,
                list(self.SUPPORTED_TYPES.keys()),
            )

        doc_type = self.SUPPORTED_TYPES[file_ext]

        # Create document record with PENDING status
        doc_metadata = DocumentMetadata(
            title=Path(filename).stem,
            source_path=filename,
            custom_metadata=metadata or {},
        )

        document = Document.create(
            filename=filename,
            document_type=doc_type,
            metadata=doc_metadata,
        )

        # Document starts as PENDING
        document.status = DocumentStatus.PENDING
        self._documents[document.document_id] = document
        self._save_document_registry()

        logger.audit(
            action="document_record_created",
            resource_type="document",
            resource_id=document.document_id,
            filename=filename,
            document_type=doc_type.value,
        )

        return document

    async def process_document_background(
        self,
        document_id: str,
        file_content: bytes,
    ) -> None:
        """Process a document in the background.

        This handles the heavy lifting: parsing, chunking, and embedding.
        Updates the document status to READY or FAILED when complete.

        Args:
            document_id: ID of the document to process
            file_content: Raw file content as bytes
        """
        document = self._documents.get(document_id)
        if not document:
            logger.error("Document not found for background processing", document_id=document_id)
            return

        # Update status to PROCESSING
        document.status = DocumentStatus.PROCESSING
        document.updated_at = datetime.now(UTC)
        self._save_document_registry()

        logger.audit(
            action="document_processing_started",
            resource_type="document",
            resource_id=document_id,
        )

        try:
            # Run blocking I/O in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()

            # Parse document content (blocking I/O)
            file_obj = io.BytesIO(file_content)
            content = await loop.run_in_executor(
                _executor,
                self._parse_document,
                file_obj,
                document.document_type,
            )
            document.metadata.word_count = len(content.split())

            # Chunk the document (CPU-bound but relatively fast)
            chunks = self.chunker.chunk_document(
                document_id=document.document_id,
                content=content,
                metadata={
                    "title": document.metadata.title,
                    "filename": document.filename,
                    **(document.metadata.custom_metadata or {}),
                },
            )

            # Add chunks to vector store (blocking I/O - embedding)
            await loop.run_in_executor(
                _executor,
                self.vector_store.add_chunks,
                chunks,
            )

            # Update document status to READY
            document.chunk_count = len(chunks)
            document.status = DocumentStatus.READY
            document.updated_at = datetime.now(UTC)

            logger.audit(
                action="document_ingested",
                resource_type="document",
                resource_id=document_id,
                chunk_count=len(chunks),
            )

        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            document.updated_at = datetime.now(UTC)
            logger.error(
                "Document background processing failed",
                document_id=document_id,
                error=str(e),
            )

        finally:
            self._save_document_registry()

    async def ingest_document(
        self,
        file: BinaryIO,
        filename: str,
        metadata: dict[str, str] | None = None,
    ) -> Document:
        """Ingest a document from an uploaded file.

        Args:
            file: File-like object with document content
            filename: Original filename
            metadata: Optional custom metadata

        Returns:
            Document object with processing status

        Raises:
            UnsupportedDocumentTypeError: If file type is not supported
            DocumentProcessingError: If processing fails
        """
        # Determine document type
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.SUPPORTED_TYPES:
            raise UnsupportedDocumentTypeError(
                file_ext,
                list(self.SUPPORTED_TYPES.keys()),
            )

        doc_type = self.SUPPORTED_TYPES[file_ext]

        # Create document record
        doc_metadata = DocumentMetadata(
            title=Path(filename).stem,
            source_path=filename,
            custom_metadata=metadata or {},
        )

        document = Document.create(
            filename=filename,
            document_type=doc_type,
            metadata=doc_metadata,
        )

        document.status = DocumentStatus.PROCESSING
        self._documents[document.document_id] = document
        self._save_document_registry()

        logger.audit(
            action="document_upload_started",
            resource_type="document",
            resource_id=document.document_id,
            filename=filename,
            document_type=doc_type.value,
        )

        try:
            # Parse document content
            content = self._parse_document(file, doc_type)
            document.metadata.word_count = len(content.split())

            # Chunk the document
            chunks = self.chunker.chunk_document(
                document_id=document.document_id,
                content=content,
                metadata={
                    "title": document.metadata.title,
                    "filename": filename,
                    **(metadata or {}),
                },
            )

            # Add chunks to vector store
            self.vector_store.add_chunks(chunks)

            # Update document status
            document.chunk_count = len(chunks)
            document.status = DocumentStatus.READY
            document.updated_at = datetime.now(UTC)

            logger.audit(
                action="document_ingested",
                resource_type="document",
                resource_id=document.document_id,
                chunk_count=len(chunks),
            )

        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            document.updated_at = datetime.now(UTC)
            logger.error(
                "Document ingestion failed",
                document_id=document.document_id,
                error=str(e),
            )
            raise DocumentProcessingError(str(e), document.document_id)

        finally:
            self._save_document_registry()

        return document

    def _parse_document(self, file: BinaryIO, doc_type: DocumentType) -> str:
        """Parse document content based on type.

        Args:
            file: File-like object
            doc_type: Document type

        Returns:
            Extracted text content
        """
        if doc_type == DocumentType.PDF:
            return self._parse_pdf(file)
        elif doc_type == DocumentType.DOCX:
            return self._parse_docx(file)
        elif doc_type == DocumentType.TXT:
            return self._parse_txt(file)
        else:
            raise DocumentProcessingError(f"Parser not implemented for {doc_type}")

    def _parse_pdf(self, file: BinaryIO) -> str:
        """Extract text from PDF."""
        try:
            reader = PdfReader(file)
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n\n".join(text_parts)
        except Exception as e:
            raise DocumentProcessingError(f"PDF parsing failed: {e}")

    def _parse_docx(self, file: BinaryIO) -> str:
        """Extract text from DOCX."""
        try:
            doc = DocxDocument(file)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            raise DocumentProcessingError(f"DOCX parsing failed: {e}")

    def _parse_txt(self, file: BinaryIO) -> str:
        """Read text file content."""
        try:
            content = file.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            return content
        except Exception as e:
            raise DocumentProcessingError(f"TXT parsing failed: {e}")

    def create_url_document_record(
        self,
        url: str,
        title: str | None = None,
    ) -> Document:
        """Create a document record for a URL source.

        Args:
            url: The URL to fetch content from
            title: Optional title (defaults to URL hostname)

        Returns:
            Document object with PENDING status
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        display_title = title or parsed.netloc or url

        doc_metadata = DocumentMetadata(
            title=display_title,
            source_path=url,
            custom_metadata={"url": url},
        )

        document = Document.create(
            filename=url,
            document_type=DocumentType.URL,
            metadata=doc_metadata,
        )

        document.status = DocumentStatus.PENDING
        self._documents[document.document_id] = document
        self._save_document_registry()

        logger.audit(
            action="url_document_record_created",
            resource_type="document",
            resource_id=document.document_id,
            url=url,
        )

        return document

    async def process_url_background(
        self,
        document_id: str,
        url: str,
    ) -> None:
        """Fetch and process a URL in the background.

        Args:
            document_id: ID of the document to process
            url: URL to fetch content from
        """
        document = self._documents.get(document_id)
        if not document:
            logger.error("Document not found for URL processing", document_id=document_id)
            return

        document.status = DocumentStatus.PROCESSING
        document.updated_at = datetime.now(UTC)
        self._save_document_registry()

        logger.audit(
            action="url_processing_started",
            resource_type="document",
            resource_id=document_id,
            url=url,
        )

        try:
            # Fetch URL content
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                _executor,
                self._fetch_and_parse_url,
                url,
            )

            if not content or len(content.strip()) < 50:
                raise DocumentProcessingError("Could not extract meaningful text from URL")

            document.metadata.word_count = len(content.split())

            # Chunk the content
            chunks = self.chunker.chunk_document(
                document_id=document.document_id,
                content=content,
                metadata={
                    "title": document.metadata.title,
                    "url": url,
                },
            )

            # Add chunks to vector store
            await loop.run_in_executor(
                _executor,
                self.vector_store.add_chunks,
                chunks,
            )

            document.chunk_count = len(chunks)
            document.status = DocumentStatus.READY
            document.updated_at = datetime.now(UTC)

            logger.audit(
                action="url_document_ingested",
                resource_type="document",
                resource_id=document_id,
                chunk_count=len(chunks),
                word_count=document.metadata.word_count,
            )

        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            document.updated_at = datetime.now(UTC)
            logger.error(
                "URL processing failed",
                document_id=document_id,
                url=url,
                error=str(e),
            )

        finally:
            self._save_document_registry()

    @staticmethod
    def _fetch_and_parse_url(url: str) -> str:
        """Fetch a URL and extract text content.

        Strips script, style, nav, footer, and header elements.
        """
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "RAG-Document-Intelligence/1.0 (Document Ingestion)"},
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove non-content elements
        for tag in soup.find_all(
            ["script", "style", "nav", "footer", "header", "aside", "noscript"]
        ):
            tag.decompose()

        # Extract text
        text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive blank lines
        lines = [line.strip() for line in text.splitlines()]
        cleaned = "\n\n".join(line for line in lines if line)

        return cleaned

    def get_document(self, document_id: str) -> Document | None:
        """Get a document by ID."""
        return self._documents.get(document_id)

    def get_document_chunks(self, document_id: str) -> list[DocumentChunk]:
        """Get all chunks for a document.

        Args:
            document_id: ID of the document

        Returns:
            List of chunks belonging to the document, sorted by chunk_index
        """
        return [chunk for chunk in self.vector_store.chunks if chunk.document_id == document_id]

    def list_documents(self) -> list[Document]:
        """List all documents."""
        return list(self._documents.values())

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its chunks.

        Args:
            document_id: ID of document to delete

        Returns:
            True if document was deleted, False if not found
        """
        if document_id not in self._documents:
            return False

        # Remove from vector store
        self.vector_store.delete_document(document_id)

        # Remove from registry
        del self._documents[document_id]
        self._save_document_registry()

        logger.audit(
            action="document_deleted",
            resource_type="document",
            resource_id=document_id,
        )

        return True


# Singleton instance
_ingestion_service: IngestionService | None = None


def get_ingestion_service() -> IngestionService:
    """Get the singleton ingestion service instance."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service
