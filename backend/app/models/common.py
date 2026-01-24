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


class RetrievalType(str, Enum):
    """Type of retrieval strategy used."""
    SIMILARITY = "similarity"
    DIVERSE = "diverse"


class DocumentRegion(str, Enum):
    """Regions within a document for diverse sampling."""
    INTRO = "intro"
    MIDDLE = "middle"
    CONCLUSION = "conclusion"


class QueryIntent(str, Enum):
    """Detected intent of a user query."""
    ANALYSIS = "analysis"
    QA = "qa"
    WRITING = "writing"


class SummaryScope(str, Enum):
    """Scope of summary requests.

    BROAD: "Summarize this document" → exploratory overview + suggested questions
    FOCUSED: "Summarize X in this document" → deep synthesis on specific topic
    """
    BROAD = "broad"
    FOCUSED = "focused"
    NOT_APPLICABLE = "not_applicable"  # For non-analysis intents


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
class DocumentCoverage:
    """Coverage statistics for a single document.

    Tracks how much of a document was seen during retrieval.
    """
    document_id: str
    document_title: str
    chunks_seen: int
    chunks_total: int
    regions_covered: list[DocumentRegion] = field(default_factory=list)
    regions_missing: list[DocumentRegion] = field(default_factory=list)

    @property
    def coverage_percentage(self) -> float:
        """Calculate coverage percentage for this document."""
        if self.chunks_total == 0:
            return 0.0
        return (self.chunks_seen / self.chunks_total) * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_title": self.document_title,
            "chunks_seen": self.chunks_seen,
            "chunks_total": self.chunks_total,
            "coverage_percentage": round(self.coverage_percentage, 1),
            "regions_covered": [r.value for r in self.regions_covered],
            "regions_missing": [r.value for r in self.regions_missing],
        }


@dataclass
class CoverageDescriptor:
    """Describes the coverage achieved by a retrieval operation.

    This is computed BEFORE prompting to condition LLM responses on
    how representative the retrieved context is.
    """
    retrieval_type: RetrievalType
    chunks_seen: int
    chunks_total: int
    coverage_percentage: float
    document_coverage: dict[str, DocumentCoverage] = field(default_factory=dict)
    blind_spots: list[str] = field(default_factory=list)
    coverage_summary: str = ""  # Human-readable summary for prompt injection

    def to_dict(self) -> dict[str, Any]:
        return {
            "retrieval_type": self.retrieval_type.value,
            "chunks_seen": self.chunks_seen,
            "chunks_total": self.chunks_total,
            "coverage_percentage": round(self.coverage_percentage, 1),
            "document_coverage": {
                doc_id: cov.to_dict()
                for doc_id, cov in self.document_coverage.items()
            },
            "blind_spots": self.blind_spots,
            "coverage_summary": self.coverage_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoverageDescriptor":
        doc_coverage = {}
        for doc_id, cov_data in data.get("document_coverage", {}).items():
            doc_coverage[doc_id] = DocumentCoverage(
                document_id=cov_data["document_id"],
                document_title=cov_data["document_title"],
                chunks_seen=cov_data["chunks_seen"],
                chunks_total=cov_data["chunks_total"],
                regions_covered=[DocumentRegion(r) for r in cov_data.get("regions_covered", [])],
                regions_missing=[DocumentRegion(r) for r in cov_data.get("regions_missing", [])],
            )
        return cls(
            retrieval_type=RetrievalType(data["retrieval_type"]),
            chunks_seen=data["chunks_seen"],
            chunks_total=data["chunks_total"],
            coverage_percentage=data["coverage_percentage"],
            document_coverage=doc_coverage,
            blind_spots=data.get("blind_spots", []),
            coverage_summary=data.get("coverage_summary", ""),
        )


@dataclass
class IntentClassification:
    """Classification of user query intent.

    Determines which retrieval strategy to use.
    For ANALYSIS intent, also determines summary scope (broad vs focused).
    """
    intent: QueryIntent
    confidence: float
    reasoning: str
    suggested_retrieval: RetrievalType
    summary_scope: SummaryScope = SummaryScope.NOT_APPLICABLE
    focus_topic: str | None = None  # Extracted topic for focused summaries

    def to_dict(self) -> dict[str, Any]:
        result = {
            "intent": self.intent.value,
            "confidence": round(self.confidence, 2),
            "reasoning": self.reasoning,
            "suggested_retrieval": self.suggested_retrieval.value,
            "summary_scope": self.summary_scope.value,
        }
        if self.focus_topic:
            result["focus_topic"] = self.focus_topic
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntentClassification":
        return cls(
            intent=QueryIntent(data["intent"]),
            confidence=data["confidence"],
            reasoning=data["reasoning"],
            suggested_retrieval=RetrievalType(data["suggested_retrieval"]),
            summary_scope=SummaryScope(data.get("summary_scope", "not_applicable")),
            focus_topic=data.get("focus_topic"),
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
    retrieval_type: RetrievalType = RetrievalType.SIMILARITY
    coverage: CoverageDescriptor | None = None
    intent: IntentClassification | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "query": self.query,
            "top_k": self.top_k,
            "similarity_threshold": self.similarity_threshold,
            "chunks_retrieved": self.chunks_retrieved,
            "chunks_above_threshold": self.chunks_above_threshold,
            "retrieval_time_ms": self.retrieval_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "retrieval_type": self.retrieval_type.value,
        }
        if self.coverage:
            result["coverage"] = self.coverage.to_dict()
        if self.intent:
            result["intent"] = self.intent.to_dict()
        return result


@dataclass
class WarningType:
    """Predefined warning types for consistency."""
    INSUFFICIENT_CONTEXT = "insufficient_context"
    LOW_RELEVANCE_SOURCES = "low_relevance_sources"
    SOURCE_OVER_RELIANCE = "source_over_reliance"
    POTENTIAL_HALLUCINATION = "potential_hallucination"
    OUTDATED_SOURCES = "outdated_sources"
    CONFLICTING_SOURCES = "conflicting_sources"
