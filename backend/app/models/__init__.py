"""Data models for the RAG writing assistant."""

from .common import (
    ConfidenceLevel,
    GeneratedSection,
    RetrievalMetadata,
    SourceReference,
    WarningType,
)
from .document import (
    ChunkingConfig,
    Document,
    DocumentChunk,
    DocumentMetadata,
    DocumentStatus,
    DocumentType,
)
from .generation import (
    GeneratedSectionResponse,
    GenerationRequest,
    GenerationResponse,
    GenerationResult,
    RegenerateSectionRequest,
    RegenerateSectionResponse,
    RegenerationResult,
    RetrievalMetadataResponse,
    SourceReferenceResponse,
)

__all__ = [
    # Common
    "ConfidenceLevel",
    "GeneratedSection",
    "RetrievalMetadata",
    "SourceReference",
    "WarningType",
    # Document
    "ChunkingConfig",
    "Document",
    "DocumentChunk",
    "DocumentMetadata",
    "DocumentStatus",
    "DocumentType",
    # Generation
    "GeneratedSectionResponse",
    "GenerationRequest",
    "GenerationResponse",
    "GenerationResult",
    "RegenerateSectionRequest",
    "RegenerateSectionResponse",
    "RegenerationResult",
    "RetrievalMetadataResponse",
    "SourceReferenceResponse",
]
