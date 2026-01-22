"""Custom exceptions for the RAG writing assistant.

These exceptions provide clear error categories for proper handling at the API layer.
"""


class RAGAssistantError(Exception):
    """Base exception for all RAG assistant errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DocumentError(RAGAssistantError):
    """Errors related to document operations."""
    pass


class DocumentNotFoundError(DocumentError):
    """Document was not found."""

    def __init__(self, document_id: str):
        super().__init__(
            f"Document not found: {document_id}",
            {"document_id": document_id},
        )


class DocumentProcessingError(DocumentError):
    """Error during document processing (parsing, chunking, etc.)."""

    def __init__(self, message: str, document_id: str | None = None):
        super().__init__(
            message,
            {"document_id": document_id} if document_id else {},
        )


class UnsupportedDocumentTypeError(DocumentError):
    """Document type is not supported."""

    def __init__(self, document_type: str, supported_types: list[str]):
        super().__init__(
            f"Unsupported document type: {document_type}. Supported types: {supported_types}",
            {"document_type": document_type, "supported_types": supported_types},
        )


class RetrievalError(RAGAssistantError):
    """Errors related to retrieval operations."""
    pass


class VectorStoreError(RetrievalError):
    """Error with vector store operations."""
    pass


class EmbeddingError(RetrievalError):
    """Error generating embeddings."""
    pass


class GenerationError(RAGAssistantError):
    """Errors related to content generation."""
    pass


class LLMError(GenerationError):
    """Error communicating with the LLM."""

    def __init__(self, message: str, model: str | None = None):
        super().__init__(
            message,
            {"model": model} if model else {},
        )


class InsufficientContextError(GenerationError):
    """Not enough context retrieved to generate content."""

    def __init__(self, chunks_found: int, minimum_required: int):
        super().__init__(
            f"Insufficient context: found {chunks_found} chunks, need at least {minimum_required}",
            {"chunks_found": chunks_found, "minimum_required": minimum_required},
        )


class ValidationError(RAGAssistantError):
    """Validation errors for requests or data."""
    pass


class ConfigurationError(RAGAssistantError):
    """Configuration or setup errors."""
    pass
