"""Health check endpoint."""

from fastapi import APIRouter

from ...rag import get_vector_store

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict:
    """Check API health status."""
    vector_store = get_vector_store()
    stats = vector_store.get_stats()

    return {
        "status": "healthy",
        "vector_store": stats,
    }
