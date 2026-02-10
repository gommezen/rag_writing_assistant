"""Application configuration using pydantic-settings.

All configuration values are loaded from environment variables with sensible defaults.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Ollama LLM settings
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "bge-m3"  # Upgraded from mxbai-embed-large
    generation_model: str = "qwen2.5:7b-instruct-q4_0"  # Default/fallback model

    # Context window (reduced for faster generation, lower VRAM)
    ollama_num_ctx: int = 4096

    # Intent-specific models
    analysis_model: str = "glm-4.7-flash"              # Higher quality for deep analysis
    writing_model: str = "qwen2.5:7b-instruct-q4_0"    # Best prose quality
    qa_model: str = "gemma3:4b"                        # Fast for simple questions

    # RAG settings
    chunk_size: int = 500
    chunk_overlap: int = 100
    similarity_threshold: float = 0.35
    top_k_retrieval: int = 10

    # Intent-specific similarity thresholds
    qa_similarity_threshold: float = 0.50      # QA needs precise matches
    analysis_similarity_threshold: float = 0.25  # Analysis needs broad coverage
    writing_similarity_threshold: float = 0.35   # Writing is balanced

    # Reranker settings
    reranker_enabled: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_initial_k: int = 20  # Retrieve more chunks for reranking

    # Confidence-based model routing
    fast_model: str = "qwen2.5:1.5b-instruct"         # HIGH confidence retrieval
    standard_model: str = "qwen2.5:7b-instruct-q4_0"  # MEDIUM confidence retrieval
    quality_model: str = "llama3.1:8b-instruct-q4_0"  # LOW confidence retrieval

    # Coverage settings for analysis mode
    default_coverage_pct: float = 35.0    # Target coverage for diverse retrieval
    max_coverage_pct: float = 60.0        # Maximum coverage (with escalation)

    # Data paths
    data_dir: Path = Path("data")
    vectors_dir: Path = Path("data/vectors")
    documents_dir: Path = Path("data/documents")
    conversations_dir: Path = Path("data/conversations")

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.vectors_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.conversations_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
