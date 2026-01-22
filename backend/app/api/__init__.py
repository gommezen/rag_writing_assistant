"""API module for the RAG writing assistant."""

from .routes import documents_router, generation_router, health_router

__all__ = [
    "documents_router",
    "generation_router",
    "health_router",
]
