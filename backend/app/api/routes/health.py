"""Health check endpoint."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ...rag import get_vector_store

router = APIRouter(tags=["Health"])


class VectorStoreStats(BaseModel):
    """Vector store statistics."""
    total_chunks: int
    total_documents: int
    index_trained: bool


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    vector_store: VectorStoreStats


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API health status."""
    vector_store = get_vector_store()
    stats = vector_store.get_stats()

    return HealthResponse(
        status="healthy",
        vector_store=VectorStoreStats(**stats),
    )
