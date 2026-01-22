"""Tests for data models."""

import pytest
from datetime import datetime

from app.models import (
    ConfidenceLevel,
    SourceReference,
    GeneratedSection,
    RetrievalMetadata,
    Document,
    DocumentMetadata,
    DocumentType,
    DocumentStatus,
    DocumentChunk,
    ChunkingConfig,
)


class TestSourceReference:
    """Tests for SourceReference model."""

    def test_create_source_reference(self):
        source = SourceReference(
            document_id="doc-1",
            chunk_id="chunk-1",
            excerpt="This is an excerpt",
            relevance_score=0.85,
            metadata={"title": "Test Doc"},
        )

        assert source.document_id == "doc-1"
        assert source.chunk_id == "chunk-1"
        assert source.excerpt == "This is an excerpt"
        assert source.relevance_score == 0.85
        assert source.metadata == {"title": "Test Doc"}

    def test_to_dict(self):
        source = SourceReference(
            document_id="doc-1",
            chunk_id="chunk-1",
            excerpt="Test",
            relevance_score=0.9,
        )

        data = source.to_dict()

        assert data["document_id"] == "doc-1"
        assert data["chunk_id"] == "chunk-1"
        assert data["excerpt"] == "Test"
        assert data["relevance_score"] == 0.9
        assert data["metadata"] == {}

    def test_from_dict(self):
        data = {
            "document_id": "doc-1",
            "chunk_id": "chunk-1",
            "excerpt": "Test excerpt",
            "relevance_score": 0.75,
            "metadata": {"author": "Test Author"},
        }

        source = SourceReference.from_dict(data)

        assert source.document_id == "doc-1"
        assert source.metadata["author"] == "Test Author"


class TestGeneratedSection:
    """Tests for GeneratedSection model."""

    def test_sources_never_none(self):
        """Sources should always be a list, never None."""
        section = GeneratedSection(
            section_id="sec-1",
            content="Test content",
            sources=[],  # Empty list, not None
            confidence=ConfidenceLevel.LOW,
        )

        assert section.sources is not None
        assert isinstance(section.sources, list)
        assert len(section.sources) == 0

    def test_confidence_levels(self):
        """All confidence levels should be valid."""
        for level in ConfidenceLevel:
            section = GeneratedSection(
                section_id="sec-1",
                content="Test",
                sources=[],
                confidence=level,
            )
            assert section.confidence == level

    def test_to_dict_preserves_all_fields(self):
        source = SourceReference(
            document_id="doc-1",
            chunk_id="chunk-1",
            excerpt="Test",
            relevance_score=0.8,
        )

        section = GeneratedSection(
            section_id="sec-1",
            content="Test content",
            sources=[source],
            confidence=ConfidenceLevel.HIGH,
            warnings=["Test warning"],
            is_user_edited=True,
        )

        data = section.to_dict()

        assert data["section_id"] == "sec-1"
        assert data["content"] == "Test content"
        assert len(data["sources"]) == 1
        assert data["confidence"] == "high"
        assert data["warnings"] == ["Test warning"]
        assert data["is_user_edited"] is True


class TestDocument:
    """Tests for Document model."""

    def test_create_document_generates_id(self):
        metadata = DocumentMetadata(title="Test Doc")
        document = Document.create(
            filename="test.pdf",
            document_type=DocumentType.PDF,
            metadata=metadata,
        )

        assert document.document_id is not None
        assert len(document.document_id) > 0
        assert document.status == DocumentStatus.PENDING

    def test_document_serialization_roundtrip(self):
        metadata = DocumentMetadata(
            title="Test Doc",
            author="Test Author",
            word_count=1000,
        )
        original = Document.create(
            filename="test.pdf",
            document_type=DocumentType.PDF,
            metadata=metadata,
        )

        data = original.to_dict()
        restored = Document.from_dict(data)

        assert restored.document_id == original.document_id
        assert restored.filename == original.filename
        assert restored.metadata.title == original.metadata.title
        assert restored.metadata.author == original.metadata.author


class TestChunkingConfig:
    """Tests for ChunkingConfig model."""

    def test_default_values(self):
        config = ChunkingConfig()

        assert config.chunk_size == 500
        assert config.chunk_overlap == 100
        assert config.separator == "\n\n"
        assert config.strategy_version == "v1.0"

    def test_custom_values(self):
        config = ChunkingConfig(
            chunk_size=1000,
            chunk_overlap=200,
            separator="\n",
        )

        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.separator == "\n"
