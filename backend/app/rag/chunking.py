"""Document chunking with deterministic, configurable strategies.

Chunking configuration is tracked for auditability - every chunk can be
reproduced given the same configuration and source document.
"""

from uuid import uuid4

from ..config import get_settings
from ..core import get_logger
from ..models import ChunkingConfig, DocumentChunk

logger = get_logger(__name__)


class DocumentChunker:
    """Deterministic document chunking with configurable parameters."""

    def __init__(self, config: ChunkingConfig | None = None):
        """Initialize chunker with configuration.

        Args:
            config: Chunking configuration. If None, uses settings defaults.
        """
        if config is None:
            settings = get_settings()
            config = ChunkingConfig(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
        self.config = config

    def chunk_document(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, str] | None = None,
    ) -> list[DocumentChunk]:
        """Split document content into chunks with metadata.

        Args:
            document_id: ID of the source document
            content: Full document text content
            metadata: Additional metadata to attach to each chunk

        Returns:
            List of DocumentChunk objects
        """
        if not content or not content.strip():
            logger.warning(
                "Empty content provided for chunking",
                document_id=document_id,
            )
            return []

        # First, try to split by paragraphs
        paragraphs = self._split_by_paragraphs(content)

        # Then chunk paragraphs respecting size limits
        chunks = self._create_chunks(
            document_id=document_id,
            paragraphs=paragraphs,
            metadata=metadata or {},
        )

        logger.info(
            "Document chunked",
            document_id=document_id,
            chunk_count=len(chunks),
            config=self.config.to_dict(),
        )

        return chunks

    def _split_by_paragraphs(self, content: str) -> list[str]:
        """Split content into paragraphs using the configured separator."""
        # Use configured separator (default: double newline)
        raw_paragraphs = content.split(self.config.separator)

        # Clean and filter empty paragraphs
        paragraphs = []
        for p in raw_paragraphs:
            cleaned = p.strip()
            if cleaned:
                paragraphs.append(cleaned)

        return paragraphs

    def _create_chunks(
        self,
        document_id: str,
        paragraphs: list[str],
        metadata: dict[str, str],
    ) -> list[DocumentChunk]:
        """Create chunks from paragraphs respecting size limits."""
        chunks: list[DocumentChunk] = []
        current_chunk_text = ""
        current_start_char = 0
        chunk_index = 0

        # Track position in original document
        char_position = 0

        for paragraph in paragraphs:
            # If adding this paragraph would exceed chunk size
            if (
                current_chunk_text
                and len(current_chunk_text) + len(paragraph) + 1 > self.config.chunk_size
            ):
                # Save current chunk
                chunk = self._create_chunk(
                    document_id=document_id,
                    content=current_chunk_text,
                    chunk_index=chunk_index,
                    start_char=current_start_char,
                    metadata=metadata,
                )
                chunks.append(chunk)
                chunk_index += 1

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk_text)
                current_chunk_text = overlap_text + paragraph if overlap_text else paragraph
                current_start_char = (
                    char_position - len(overlap_text) if overlap_text else char_position
                )
            else:
                # Add paragraph to current chunk
                if current_chunk_text:
                    current_chunk_text += " " + paragraph
                else:
                    current_chunk_text = paragraph
                    current_start_char = char_position

            # Update position (paragraph + separator)
            char_position += len(paragraph) + len(self.config.separator)

        # Don't forget the last chunk
        if current_chunk_text:
            chunk = self._create_chunk(
                document_id=document_id,
                content=current_chunk_text,
                chunk_index=chunk_index,
                start_char=current_start_char,
                metadata=metadata,
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        document_id: str,
        content: str,
        chunk_index: int,
        start_char: int,
        metadata: dict[str, str],
    ) -> DocumentChunk:
        """Create a single chunk with all metadata."""
        return DocumentChunk(
            chunk_id=str(uuid4()),
            document_id=document_id,
            content=content,
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=start_char + len(content),
            metadata={
                **metadata,
                "chunk_strategy": self.config.strategy_version,
                "chunk_size": str(self.config.chunk_size),
                "chunk_overlap": str(self.config.chunk_overlap),
            },
        )

    def _get_overlap_text(self, text: str) -> str:
        """Get the overlap portion from the end of text."""
        if len(text) <= self.config.chunk_overlap:
            return text

        # Try to break at word boundary
        overlap_start = len(text) - self.config.chunk_overlap
        space_idx = text.find(" ", overlap_start)

        if space_idx != -1 and space_idx < len(text):
            return text[space_idx + 1 :]

        return text[overlap_start:]


def create_chunker(config: ChunkingConfig | None = None) -> DocumentChunker:
    """Factory function to create a document chunker."""
    return DocumentChunker(config)
