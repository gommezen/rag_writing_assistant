"""Core utilities for the RAG writing assistant."""

from .exceptions import (
    ConfigurationError,
    DocumentError,
    DocumentNotFoundError,
    DocumentProcessingError,
    EmbeddingError,
    GenerationError,
    InsufficientContextError,
    LLMError,
    RAGAssistantError,
    RetrievalError,
    UnsupportedDocumentTypeError,
    ValidationError,
    VectorStoreError,
)
from .logging import AuditLogger, get_logger

__all__ = [
    # Exceptions
    "ConfigurationError",
    "DocumentError",
    "DocumentNotFoundError",
    "DocumentProcessingError",
    "EmbeddingError",
    "GenerationError",
    "InsufficientContextError",
    "LLMError",
    "RAGAssistantError",
    "RetrievalError",
    "UnsupportedDocumentTypeError",
    "ValidationError",
    "VectorStoreError",
    # Logging
    "AuditLogger",
    "get_logger",
]
