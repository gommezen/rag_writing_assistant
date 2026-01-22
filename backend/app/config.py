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
    embedding_model: str = "mxbai-embed-large"
    generation_model: str = "llama3.1:8b-instruct-q4_0"

    # RAG settings
    chunk_size: int = 500
    chunk_overlap: int = 100
    similarity_threshold: float = 0.35
    top_k_retrieval: int = 10

    # Data paths
    data_dir: Path = Path("data")
    vectors_dir: Path = Path("data/vectors")
    documents_dir: Path = Path("data/documents")

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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
