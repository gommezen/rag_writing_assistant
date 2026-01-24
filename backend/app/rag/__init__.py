"""RAG components for the writing assistant."""

from .chunking import DocumentChunker, create_chunker
from .embedding import EmbeddingService, get_embedding_service
from .prompts import (
    PromptTemplates,
    build_analysis_prompt,
    build_chat_prompt,
    build_coverage_aware_generation_prompt,
    build_exploratory_summary_prompt,
    build_focused_summary_prompt,
    build_generation_prompt,
    build_regeneration_prompt,
    build_suggested_questions_prompt,
    extract_citations,
    format_context,
    parse_questions,
    sanitize_citations,
)
from .vectorstore import VectorStore, get_vector_store

__all__ = [
    # Chunking
    "DocumentChunker",
    "create_chunker",
    # Embedding
    "EmbeddingService",
    "get_embedding_service",
    # Prompts
    "PromptTemplates",
    "build_analysis_prompt",
    "build_chat_prompt",
    "build_coverage_aware_generation_prompt",
    "build_exploratory_summary_prompt",
    "build_focused_summary_prompt",
    "build_generation_prompt",
    "build_regeneration_prompt",
    "build_suggested_questions_prompt",
    "extract_citations",
    "format_context",
    "parse_questions",
    "sanitize_citations",
    # Vector store
    "VectorStore",
    "get_vector_store",
]
