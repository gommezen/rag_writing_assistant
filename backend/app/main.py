"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import chat_router, documents_router, generation_router, health_router
from .config import get_settings
from .core import RAGAssistantError, get_logger

logger = get_logger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown logic."""
    logger.info(
        "Starting RAG Writing Assistant",
        ollama_url=settings.ollama_base_url,
        embedding_model=settings.embedding_model,
        generation_model=settings.generation_model,
    )
    settings.ensure_directories()
    yield
    logger.info("Shutting down RAG Writing Assistant")


app = FastAPI(
    title="RAG Writing Assistant",
    description="A governance-first RAG writing assistant for enterprise use",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(RAGAssistantError)
async def rag_exception_handler(request: Request, exc: RAGAssistantError) -> JSONResponse:
    """Handle RAG assistant specific errors."""
    logger.error(
        "Request error",
        path=request.url.path,
        error=exc.message,
        details=exc.details,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": exc.message,
            "details": exc.details,
        },
    )


# Include routers
app.include_router(health_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(generation_router, prefix="/api")
app.include_router(chat_router, prefix="/api")



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
