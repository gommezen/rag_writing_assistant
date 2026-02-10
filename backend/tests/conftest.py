"""Centralized fixtures and mocks for testing.

Provides deterministic mocks for external services (Ollama, embeddings)
and factory fixtures for common test data.
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from app.config import Settings
from app.models import (
    ChunkingConfig,
    ConfidenceLevel,
    Document,
    DocumentChunk,
    DocumentMetadata,
    DocumentStatus,
    DocumentType,
    GeneratedSection,
    RetrievalMetadata,
    SourceReference,
)
from fastapi.testclient import TestClient

# ============================================================================
# Mock Classes for External Services
# ============================================================================


class MockOllamaEmbeddings:
    """Mock embedding service that returns deterministic embeddings.

    Uses text hashing to produce reproducible embeddings for the same input.
    """

    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self._dimension = 384  # Common embedding dimension

    def _hash_to_embedding(self, text: str) -> list[float]:
        """Convert text to deterministic embedding via hashing."""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Expand hash to embedding dimension
        embedding = []
        for i in range(self._dimension):
            # Use hash bytes cyclically
            byte_val = hash_bytes[i % len(hash_bytes)]
            # Normalize to [-1, 1] range
            embedding.append((byte_val - 128) / 128.0)
        return embedding

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single query text."""
        return self._hash_to_embedding(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return [self._hash_to_embedding(text) for text in texts]

    # EmbeddingService interface methods
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text (EmbeddingService interface)."""
        return self._hash_to_embedding(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (EmbeddingService interface)."""
        return [self._hash_to_embedding(text) for text in texts]


class MockChatOllama:
    """Mock LLM that returns deterministic responses with citations."""

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
    ):
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self._response_content = None

    def set_response(self, content: str) -> None:
        """Set the response content for the next call."""
        self._response_content = content

    async def ainvoke(self, messages: list) -> MagicMock:
        """Async invoke that returns a mock response."""
        if self._response_content:
            content = self._response_content
            self._response_content = None  # Reset after use
        else:
            # Default response with citations
            content = (
                "Based on the provided context, here is the requested content. "
                "[Source 1] This is the first key point from the context. "
                "[Source 2] This is the second point with supporting evidence.\n\n"
                "Additionally, [Source 1] provides more context for this topic."
            )

        response = MagicMock()
        response.content = content
        return response


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "vectors").mkdir(exist_ok=True)
    (data_dir / "documents").mkdir(exist_ok=True)
    return data_dir


@pytest.fixture
def mock_settings(temp_data_dir: Path) -> Settings:
    """Create test settings with temporary directories."""
    return Settings(
        data_dir=temp_data_dir,
        vectors_dir=temp_data_dir / "vectors",
        documents_dir=temp_data_dir / "documents",
        ollama_base_url="http://localhost:11434",
        embedding_model="nomic-embed-text",
        generation_model="llama3.2",
        # Intent-specific models (all using same mock model for tests)
        analysis_model="llama3.2",
        writing_model="llama3.2",
        qa_model="llama3.2",
        ollama_num_ctx=8192,
        chunk_size=100,
        chunk_overlap=20,
        similarity_threshold=0.5,
        top_k_retrieval=5,
        log_level="WARNING",
    )


@pytest.fixture
def mock_embedding_service() -> MockOllamaEmbeddings:
    """Create a mock embedding service."""
    return MockOllamaEmbeddings()


@pytest.fixture
def mock_llm() -> MockChatOllama:
    """Create a mock LLM."""
    return MockChatOllama()


# ============================================================================
# Document Fixtures
# ============================================================================


@pytest.fixture
def sample_document_metadata() -> DocumentMetadata:
    """Create sample document metadata."""
    return DocumentMetadata(
        title="Test Document",
        author="Test Author",
        created_date=datetime(2024, 1, 1),
        source_path="test_document.pdf",
        page_count=10,
        word_count=1500,
        custom_metadata={"category": "testing"},
    )


@pytest.fixture
def sample_document(sample_document_metadata: DocumentMetadata) -> Document:
    """Create a sample document."""
    return Document(
        document_id=str(uuid4()),
        filename="test_document.pdf",
        document_type=DocumentType.PDF,
        status=DocumentStatus.READY,
        metadata=sample_document_metadata,
        chunk_count=15,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_document_factory():
    """Factory for creating multiple documents with different properties."""

    def _create(
        document_id: str | None = None,
        filename: str = "test.pdf",
        doc_type: DocumentType = DocumentType.PDF,
        status: DocumentStatus = DocumentStatus.READY,
        title: str = "Test Document",
        chunk_count: int = 10,
    ) -> Document:
        return Document(
            document_id=document_id or str(uuid4()),
            filename=filename,
            document_type=doc_type,
            status=status,
            metadata=DocumentMetadata(title=title),
            chunk_count=chunk_count,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    return _create


# ============================================================================
# Chunk Fixtures
# ============================================================================


@pytest.fixture
def sample_chunk() -> DocumentChunk:
    """Create a single sample chunk."""
    return DocumentChunk(
        chunk_id="chunk-001",
        document_id="doc-001",
        content="This is sample content for testing purposes.",
        chunk_index=0,
        start_char=0,
        end_char=45,
        page_number=1,
        metadata={"title": "Test Document", "chunk_strategy": "v1.0"},
    )


@pytest.fixture
def sample_chunks() -> list[DocumentChunk]:
    """Create a list of sample chunks for testing."""
    return [
        DocumentChunk(
            chunk_id=f"chunk-{i:03d}",
            document_id="doc-001",
            content=f"This is test content for chunk {i}. It contains information about topic {i}.",
            chunk_index=i,
            start_char=i * 100,
            end_char=(i + 1) * 100,
            page_number=i // 5 + 1,
            metadata={"title": "Test Document", "chunk_strategy": "v1.0"},
        )
        for i in range(5)
    ]


@pytest.fixture
def sample_chunks_factory():
    """Factory for creating chunks with custom properties."""

    def _create(
        document_id: str = "doc-001",
        count: int = 5,
        content_prefix: str = "Test content",
        metadata: dict | None = None,
    ) -> list[DocumentChunk]:
        return [
            DocumentChunk(
                chunk_id=f"{document_id}-chunk-{i:03d}",
                document_id=document_id,
                content=f"{content_prefix} for chunk {i}.",
                chunk_index=i,
                start_char=i * 50,
                end_char=(i + 1) * 50,
                metadata=metadata or {"title": "Test Document"},
            )
            for i in range(count)
        ]

    return _create


# ============================================================================
# Source Reference Fixtures
# ============================================================================


@pytest.fixture
def sample_source() -> SourceReference:
    """Create a single sample source reference."""
    return SourceReference(
        document_id="doc-001",
        chunk_id="chunk-001",
        excerpt="This is an excerpt from the source document...",
        relevance_score=0.85,
        metadata={"title": "Test Document", "filename": "test.pdf"},
    )


@pytest.fixture
def sample_sources() -> list[SourceReference]:
    """Create a list of sample source references."""
    return [
        SourceReference(
            document_id="doc-001",
            chunk_id=f"chunk-{i:03d}",
            excerpt=f"Excerpt from source {i} with relevant information.",
            relevance_score=0.9 - (i * 0.1),
            metadata={"title": f"Document {i}", "filename": f"doc{i}.pdf"},
        )
        for i in range(1, 4)
    ]


@pytest.fixture
def sample_sources_factory():
    """Factory for creating source references with custom properties."""

    def _create(
        count: int = 3,
        document_id: str = "doc-001",
        base_score: float = 0.9,
    ) -> list[SourceReference]:
        return [
            SourceReference(
                document_id=document_id,
                chunk_id=f"chunk-{i:03d}",
                excerpt=f"Source excerpt {i} with content.",
                relevance_score=max(0.1, base_score - (i * 0.1)),
                metadata={"title": "Test Document"},
            )
            for i in range(count)
        ]

    return _create


# ============================================================================
# Section and Generation Fixtures
# ============================================================================


@pytest.fixture
def sample_section(sample_sources: list[SourceReference]) -> GeneratedSection:
    """Create a sample generated section."""
    return GeneratedSection(
        section_id="section-001",
        content="This is generated content. [Source 1] It references sources. [Source 2]",
        sources=sample_sources,
        confidence=ConfidenceLevel.HIGH,
        warnings=[],
        is_user_edited=False,
    )


@pytest.fixture
def sample_retrieval_metadata() -> RetrievalMetadata:
    """Create sample retrieval metadata."""
    return RetrievalMetadata(
        query="test query",
        top_k=10,
        similarity_threshold=0.7,
        chunks_retrieved=5,
        chunks_above_threshold=3,
        retrieval_time_ms=15.5,
        timestamp=datetime.now(UTC),
    )


# ============================================================================
# Vector Store Fixtures
# ============================================================================


@pytest.fixture
def in_memory_vector_store(mock_settings: Settings, mock_embedding_service: MockOllamaEmbeddings):
    """Create an isolated in-memory vector store for each test."""
    from app.rag.vectorstore import VectorStore

    # Patch the embedding service
    with patch("app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service):
        with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
            store = VectorStore(store_path=mock_settings.vectors_dir)
            yield store


# ============================================================================
# Service Fixtures with Mocks
# ============================================================================


@pytest.fixture
def mock_services(
    mock_settings: Settings, mock_embedding_service: MockOllamaEmbeddings, mock_llm: MockChatOllama
):
    """Patch all singleton services with mocks."""
    with patch("app.config.get_settings", return_value=mock_settings):
        with patch("app.rag.embedding.get_settings", return_value=mock_settings):
            with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                with patch(
                    "app.rag.vectorstore.get_embedding_service", return_value=mock_embedding_service
                ):
                    with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                        with patch(
                            "app.services.generation.get_settings", return_value=mock_settings
                        ):
                            yield {
                                "settings": mock_settings,
                                "embedding_service": mock_embedding_service,
                                "llm": mock_llm,
                            }


# ============================================================================
# API Test Client Fixtures
# ============================================================================


@pytest.fixture
def test_client(mock_services):
    """Create a FastAPI test client with mocked services."""
    # Reset singleton instances before creating client
    import app.rag.embedding as embedding_module
    import app.rag.vectorstore as vectorstore_module
    import app.services.diverse_retrieval as diverse_retrieval_module
    import app.services.generation as generation_module
    import app.services.ingestion as ingestion_module
    import app.services.intent as intent_module
    import app.services.retrieval as retrieval_module

    # Clear singletons
    ingestion_module._ingestion_service = None
    retrieval_module._retrieval_service = None
    generation_module._generation_service = None
    intent_module._intent_service = None
    diverse_retrieval_module._diverse_retrieval_service = None
    vectorstore_module._vector_store = None
    embedding_module._embedding_service = None

    from app.main import app

    with TestClient(app) as client:
        yield client

    # Clean up singletons after test
    ingestion_module._ingestion_service = None
    retrieval_module._retrieval_service = None
    generation_module._generation_service = None
    intent_module._intent_service = None
    diverse_retrieval_module._diverse_retrieval_service = None
    vectorstore_module._vector_store = None
    embedding_module._embedding_service = None


# ============================================================================
# File Fixtures for Testing Document Parsing
# ============================================================================


@pytest.fixture
def sample_txt_file() -> tuple[BinaryIO, str]:
    """Create a sample TXT file for testing."""
    import io

    content = b"This is a test document.\n\nIt has multiple paragraphs.\n\nFor testing purposes."
    return io.BytesIO(content), "test_document.txt"


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Create minimal PDF content for testing.

    Note: This creates a minimal valid PDF structure. For full PDF testing,
    use actual PDF files or a PDF generation library.
    """
    # Minimal PDF with text content
    # This is a simplified structure - real PDFs are more complex
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000206 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
300
%%EOF
"""


@pytest.fixture
def create_temp_txt_file(tmp_path: Path):
    """Factory to create temporary text files with custom content."""

    def _create(content: str, filename: str = "test.txt") -> Path:
        file_path = tmp_path / filename
        file_path.write_text(content)
        return file_path

    return _create


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def chunking_config() -> ChunkingConfig:
    """Create a chunking configuration for testing."""
    return ChunkingConfig(
        chunk_size=100,
        chunk_overlap=20,
        separator="\n\n",
        strategy_version="v1.0",
    )


@pytest.fixture
def assert_rag_metadata():
    """Helper to verify RAG metadata is present and valid."""

    def _assert(response_data: dict):
        # Verify sources array is never null
        if "sections" in response_data:
            for section in response_data["sections"]:
                assert section.get("sources") is not None, "sources should never be null"
                assert isinstance(section["sources"], list), "sources should be a list"
                assert section.get("confidence") is not None, "confidence should be present"
                assert section.get("warnings") is not None, "warnings should be present"

        # Verify retrieval metadata
        if "retrieval_metadata" in response_data:
            metadata = response_data["retrieval_metadata"]
            assert "query" in metadata
            assert "chunks_retrieved" in metadata
            assert "retrieval_time_ms" in metadata

    return _assert
