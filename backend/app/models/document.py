"""Document-related data models.

Models for document upload, storage, and chunk management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


@dataclass
class DocumentMetadata:
    """Metadata extracted from or assigned to a document."""
    title: str
    author: str | None = None
    created_date: datetime | None = None
    source_path: str | None = None
    page_count: int | None = None
    word_count: int | None = None
    custom_metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "author": self.author,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "source_path": self.source_path,
            "page_count": self.page_count,
            "word_count": self.word_count,
            "custom_metadata": self.custom_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentMetadata":
        created_date = None
        if data.get("created_date"):
            created_date = datetime.fromisoformat(data["created_date"])

        return cls(
            title=data["title"],
            author=data.get("author"),
            created_date=created_date,
            source_path=data.get("source_path"),
            page_count=data.get("page_count"),
            word_count=data.get("word_count"),
            custom_metadata=data.get("custom_metadata", {}),
        )


@dataclass
class DocumentChunk:
    """A chunk of document content with metadata for retrieval."""
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    page_number: int | None = None
    section_title: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentChunk":
        return cls(
            chunk_id=data["chunk_id"],
            document_id=data["document_id"],
            content=data["content"],
            chunk_index=data["chunk_index"],
            start_char=data["start_char"],
            end_char=data["end_char"],
            page_number=data.get("page_number"),
            section_title=data.get("section_title"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Document:
    """A document in the system with full metadata and processing status."""
    document_id: str
    filename: str
    document_type: DocumentType
    status: DocumentStatus
    metadata: DocumentMetadata
    chunk_count: int = 0
    raw_content: str | None = None  # Only stored temporarily during processing
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error_message: str | None = None

    @classmethod
    def create(
        cls,
        filename: str,
        document_type: DocumentType,
        metadata: DocumentMetadata,
    ) -> "Document":
        """Factory method to create a new document with a generated ID."""
        return cls(
            document_id=str(uuid4()),
            filename=filename,
            document_type=document_type,
            status=DocumentStatus.PENDING,
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "document_type": self.document_type.value,
            "status": self.status.value,
            "metadata": self.metadata.to_dict(),
            "chunk_count": self.chunk_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        return cls(
            document_id=data["document_id"],
            filename=data["filename"],
            document_type=DocumentType(data["document_type"]),
            status=DocumentStatus(data["status"]),
            metadata=DocumentMetadata.from_dict(data["metadata"]),
            chunk_count=data.get("chunk_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            error_message=data.get("error_message"),
        )


@dataclass
class ChunkingConfig:
    """Configuration for document chunking - tracked for auditability."""
    chunk_size: int = 500
    chunk_overlap: int = 100
    separator: str = "\n\n"
    strategy_version: str = "v1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "separator": self.separator,
            "strategy_version": self.strategy_version,
        }
