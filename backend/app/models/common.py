"""Common data models used across the RAG writing assistant.

These models form the foundation for all services and ensure RAG metadata
(sources, confidence, warnings) is never silently dropped.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ConfidenceLevel(str, Enum):
    """Confidence levels for generated content.

    'unknown' means we couldn't determine confidence, not that it's high.
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class SourceReference:
    """Reference to a source chunk used in generation.

    This model ensures every piece of generated content is traceable
    back to its source documents.
    """
    document_id: str
    chunk_id: str
    excerpt: str
    relevance_score: float
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "excerpt": self.excerpt,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceReference":
        return cls(
            document_id=data["document_id"],
            chunk_id=data["chunk_id"],
            excerpt=data["excerpt"],
            relevance_score=data["relevance_score"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class GeneratedSection:
    """A section of generated content with full RAG metadata.

    sources is never optional - if no sources were found, it's an empty list
    and appropriate warnings should be included.
    """
    section_id: str
    content: str
    sources: list[SourceReference]  # Never optional - empty list if none found
    confidence: ConfidenceLevel
    warnings: list[str] = field(default_factory=list)
    is_user_edited: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "content": self.content,
            "sources": [s.to_dict() for s in self.sources],
            "confidence": self.confidence.value,
            "warnings": self.warnings,
            "is_user_edited": self.is_user_edited,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GeneratedSection":
        return cls(
            section_id=data["section_id"],
            content=data["content"],
            sources=[SourceReference.from_dict(s) for s in data["sources"]],
            confidence=ConfidenceLevel(data["confidence"]),
            warnings=data.get("warnings", []),
            is_user_edited=data.get("is_user_edited", False),
        )


@dataclass
class RetrievalMetadata:
    """Metadata about the retrieval process for auditability."""
    query: str
    top_k: int
    similarity_threshold: float
    chunks_retrieved: int
    chunks_above_threshold: int
    retrieval_time_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "top_k": self.top_k,
            "similarity_threshold": self.similarity_threshold,
            "chunks_retrieved": self.chunks_retrieved,
            "chunks_above_threshold": self.chunks_above_threshold,
            "retrieval_time_ms": self.retrieval_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class WarningType:
    """Predefined warning types for consistency."""
    INSUFFICIENT_CONTEXT = "insufficient_context"
    LOW_RELEVANCE_SOURCES = "low_relevance_sources"
    SOURCE_OVER_RELIANCE = "source_over_reliance"
    POTENTIAL_HALLUCINATION = "potential_hallucination"
    OUTDATED_SOURCES = "outdated_sources"
    CONFLICTING_SOURCES = "conflicting_sources"
