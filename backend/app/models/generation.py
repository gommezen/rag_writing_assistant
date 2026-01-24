"""Generation-related request and response models.

These models define the API contracts for generation endpoints.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from .common import (
    ConfidenceLevel,
    CoverageDescriptor,
    DocumentRegion,
    GeneratedSection,
    IntentClassification,
    QueryIntent,
    RetrievalMetadata,
    RetrievalType,
    SourceReference,
    SummaryScope,
)


# Pydantic models for API request/response validation


class SourceReferenceResponse(BaseModel):
    """API response model for source reference."""
    document_id: str
    chunk_id: str
    excerpt: str
    relevance_score: float
    metadata: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_dataclass(cls, source: SourceReference) -> "SourceReferenceResponse":
        return cls(
            document_id=source.document_id,
            chunk_id=source.chunk_id,
            excerpt=source.excerpt,
            relevance_score=source.relevance_score,
            metadata=source.metadata,
        )


class GeneratedSectionResponse(BaseModel):
    """API response model for a generated section."""
    section_id: str
    content: str
    sources: list[SourceReferenceResponse]  # Never null, empty list if no sources
    confidence: ConfidenceLevel
    warnings: list[str] = Field(default_factory=list)
    is_user_edited: bool = False

    @classmethod
    def from_dataclass(cls, section: GeneratedSection) -> "GeneratedSectionResponse":
        return cls(
            section_id=section.section_id,
            content=section.content,
            sources=[SourceReferenceResponse.from_dataclass(s) for s in section.sources],
            confidence=section.confidence,
            warnings=section.warnings,
            is_user_edited=section.is_user_edited,
        )


class DocumentCoverageResponse(BaseModel):
    """API response model for document coverage."""
    document_id: str
    document_title: str
    chunks_seen: int
    chunks_total: int
    coverage_percentage: float
    regions_covered: list[str]
    regions_missing: list[str]


class CoverageDescriptorResponse(BaseModel):
    """API response model for coverage descriptor."""
    retrieval_type: str
    chunks_seen: int
    chunks_total: int
    coverage_percentage: float
    document_coverage: dict[str, DocumentCoverageResponse]
    blind_spots: list[str]
    coverage_summary: str

    @classmethod
    def from_dataclass(cls, coverage: CoverageDescriptor) -> "CoverageDescriptorResponse":
        return cls(
            retrieval_type=coverage.retrieval_type.value,
            chunks_seen=coverage.chunks_seen,
            chunks_total=coverage.chunks_total,
            coverage_percentage=round(coverage.coverage_percentage, 1),
            document_coverage={
                doc_id: DocumentCoverageResponse(
                    document_id=doc_cov.document_id,
                    document_title=doc_cov.document_title,
                    chunks_seen=doc_cov.chunks_seen,
                    chunks_total=doc_cov.chunks_total,
                    coverage_percentage=round(doc_cov.coverage_percentage, 1),
                    regions_covered=[r.value for r in doc_cov.regions_covered],
                    regions_missing=[r.value for r in doc_cov.regions_missing],
                )
                for doc_id, doc_cov in coverage.document_coverage.items()
            },
            blind_spots=coverage.blind_spots,
            coverage_summary=coverage.coverage_summary,
        )


class IntentClassificationResponse(BaseModel):
    """API response model for intent classification."""
    intent: str
    confidence: float
    reasoning: str
    suggested_retrieval: str
    summary_scope: str = "not_applicable"
    focus_topic: str | None = None

    @classmethod
    def from_dataclass(cls, intent: IntentClassification) -> "IntentClassificationResponse":
        return cls(
            intent=intent.intent.value,
            confidence=round(intent.confidence, 2),
            reasoning=intent.reasoning,
            suggested_retrieval=intent.suggested_retrieval.value,
            summary_scope=intent.summary_scope.value,
            focus_topic=intent.focus_topic,
        )


class RetrievalMetadataResponse(BaseModel):
    """API response model for retrieval metadata."""
    query: str
    top_k: int
    similarity_threshold: float
    chunks_retrieved: int
    chunks_above_threshold: int
    retrieval_time_ms: float
    timestamp: str
    retrieval_type: str = "similarity"
    coverage: CoverageDescriptorResponse | None = None
    intent: IntentClassificationResponse | None = None

    @classmethod
    def from_dataclass(cls, metadata: RetrievalMetadata) -> "RetrievalMetadataResponse":
        return cls(
            query=metadata.query,
            top_k=metadata.top_k,
            similarity_threshold=metadata.similarity_threshold,
            chunks_retrieved=metadata.chunks_retrieved,
            chunks_above_threshold=metadata.chunks_above_threshold,
            retrieval_time_ms=metadata.retrieval_time_ms,
            timestamp=metadata.timestamp.isoformat(),
            retrieval_type=metadata.retrieval_type.value,
            coverage=CoverageDescriptorResponse.from_dataclass(metadata.coverage) if metadata.coverage else None,
            intent=IntentClassificationResponse.from_dataclass(metadata.intent) if metadata.intent else None,
        )


class GenerationRequest(BaseModel):
    """Request to generate a new draft."""
    prompt: str = Field(..., min_length=1, max_length=10000, description="The writing prompt")
    document_ids: list[str] | None = Field(
        default=None,
        description="Specific documents to use. If None, uses all documents.",
    )
    max_sections: int = Field(default=5, ge=1, le=20, description="Maximum sections to generate")
    intent_override: str | None = Field(
        default=None,
        description="Override detected intent. Options: 'analysis', 'qa', 'writing'",
    )
    retrieval_type_override: str | None = Field(
        default=None,
        description="Override retrieval strategy. Options: 'similarity', 'diverse'",
    )
    escalate_coverage: bool = Field(
        default=False,
        description="Increase chunk sampling for more comprehensive coverage",
    )

    model_config = {"extra": "forbid"}


class RegenerateSectionRequest(BaseModel):
    """Request to regenerate a specific section."""
    section_id: str = Field(..., description="ID of the section to regenerate")
    original_content: str = Field(
        ...,
        min_length=1,
        description="The original content of the section to regenerate",
    )
    refinement_prompt: str | None = Field(
        default=None,
        description="Optional refinement prompt for this section",
    )
    document_ids: list[str] | None = Field(
        default=None,
        description="Specific documents to use for this section",
    )

    model_config = {"extra": "forbid"}


class GenerationResponse(BaseModel):
    """Response containing generated content with full RAG metadata."""
    generation_id: str
    sections: list[GeneratedSectionResponse]
    retrieval_metadata: RetrievalMetadataResponse
    total_sources_used: int
    generation_time_ms: float
    model_used: str
    created_at: str

    model_config = {"extra": "forbid"}


class RegenerateSectionResponse(BaseModel):
    """Response for section regeneration."""
    section: GeneratedSectionResponse
    retrieval_metadata: RetrievalMetadataResponse
    generation_time_ms: float

    model_config = {"extra": "forbid"}


class SuggestedQuestionsRequest(BaseModel):
    """Request to generate suggested questions based on documents."""
    document_ids: list[str] | None = Field(
        default=None,
        description="Specific documents to use. If None, uses all documents.",
    )
    num_questions: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of questions to generate",
    )

    model_config = {"extra": "forbid"}


class SuggestedQuestionsResponse(BaseModel):
    """Response containing suggested questions."""
    questions: list[str]
    source_documents: list[str]  # Document IDs that were used
    generation_time_ms: float

    model_config = {"extra": "forbid"}


# Internal dataclasses for service layer


@dataclass
class GenerationResult:
    """Internal result from generation service."""
    generation_id: str
    sections: list[GeneratedSection]
    retrieval_metadata: RetrievalMetadata
    total_sources_used: int
    generation_time_ms: float
    model_used: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_response(self) -> GenerationResponse:
        """Convert to API response model."""
        return GenerationResponse(
            generation_id=self.generation_id,
            sections=[GeneratedSectionResponse.from_dataclass(s) for s in self.sections],
            retrieval_metadata=RetrievalMetadataResponse.from_dataclass(self.retrieval_metadata),
            total_sources_used=self.total_sources_used,
            generation_time_ms=self.generation_time_ms,
            model_used=self.model_used,
            created_at=self.created_at.isoformat(),
        )


@dataclass
class RegenerationResult:
    """Internal result from section regeneration."""
    section: GeneratedSection
    retrieval_metadata: RetrievalMetadata
    generation_time_ms: float

    def to_response(self) -> RegenerateSectionResponse:
        """Convert to API response model."""
        return RegenerateSectionResponse(
            section=GeneratedSectionResponse.from_dataclass(self.section),
            retrieval_metadata=RetrievalMetadataResponse.from_dataclass(self.retrieval_metadata),
            generation_time_ms=self.generation_time_ms,
        )
