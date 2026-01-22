"""Tests for document chunking."""

import pytest

from app.models import ChunkingConfig
from app.rag.chunking import DocumentChunker


class TestDocumentChunker:
    """Tests for DocumentChunker."""

    def test_empty_content_returns_empty_list(self):
        chunker = DocumentChunker()
        chunks = chunker.chunk_document("doc-1", "")

        assert chunks == []

    def test_whitespace_only_returns_empty_list(self):
        chunker = DocumentChunker()
        chunks = chunker.chunk_document("doc-1", "   \n\n   ")

        assert chunks == []

    def test_single_paragraph_creates_one_chunk(self):
        chunker = DocumentChunker(
            ChunkingConfig(chunk_size=1000, chunk_overlap=100)
        )
        content = "This is a single paragraph of text."
        chunks = chunker.chunk_document("doc-1", content)

        assert len(chunks) == 1
        assert chunks[0].content == content
        assert chunks[0].document_id == "doc-1"
        assert chunks[0].chunk_index == 0

    def test_multiple_paragraphs_split_correctly(self):
        chunker = DocumentChunker(
            ChunkingConfig(chunk_size=50, chunk_overlap=10)
        )
        content = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
        chunks = chunker.chunk_document("doc-1", content)

        assert len(chunks) > 1
        # All chunks should have the same document_id
        assert all(c.document_id == "doc-1" for c in chunks)
        # Chunk indices should be sequential
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunks_contain_metadata(self):
        chunker = DocumentChunker()
        metadata = {"title": "Test Doc", "author": "Test Author"}
        chunks = chunker.chunk_document("doc-1", "Test content", metadata)

        assert len(chunks) == 1
        assert chunks[0].metadata["title"] == "Test Doc"
        assert chunks[0].metadata["author"] == "Test Author"
        # Strategy version should also be in metadata
        assert "chunk_strategy" in chunks[0].metadata

    def test_chunk_ids_are_unique(self):
        chunker = DocumentChunker(
            ChunkingConfig(chunk_size=50, chunk_overlap=10)
        )
        content = "Para one.\n\nPara two.\n\nPara three.\n\nPara four."
        chunks = chunker.chunk_document("doc-1", content)

        chunk_ids = [c.chunk_id for c in chunks]
        assert len(chunk_ids) == len(set(chunk_ids))  # All unique

    def test_char_positions_are_tracked(self):
        chunker = DocumentChunker(
            ChunkingConfig(chunk_size=1000, chunk_overlap=0)
        )
        content = "First paragraph.\n\nSecond paragraph."
        chunks = chunker.chunk_document("doc-1", content)

        # First chunk should start at 0
        assert chunks[0].start_char == 0
        # End char should be after start
        assert chunks[0].end_char > chunks[0].start_char

    def test_deterministic_chunking(self):
        """Same input should always produce same output."""
        config = ChunkingConfig(chunk_size=100, chunk_overlap=20)
        content = "Para one text here.\n\nPara two text here.\n\nPara three."

        chunker1 = DocumentChunker(config)
        chunker2 = DocumentChunker(config)

        chunks1 = chunker1.chunk_document("doc-1", content)
        chunks2 = chunker2.chunk_document("doc-1", content)

        # Same number of chunks
        assert len(chunks1) == len(chunks2)

        # Same content (IDs will differ due to UUIDs)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.content == c2.content
            assert c1.chunk_index == c2.chunk_index
