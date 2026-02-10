"""Embedding migration utility for upgrading to new embedding models.

Usage:
    python -m app.scripts.migrate_embeddings

Process:
1. Backup existing index
2. Load all chunks from metadata
3. Re-embed with new model
4. Rebuild FAISS index
5. Verify integrity

This script migrates from mxbai-embed-large to bge-m3 embeddings.
"""

import argparse
import pickle
import shutil
import sys
from datetime import datetime
from pathlib import Path

import faiss
import numpy as np


def get_backup_path(vectors_dir: Path) -> Path:
    """Generate timestamped backup path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return vectors_dir.parent / f"vectors_backup_{timestamp}"


def backup_index(vectors_dir: Path) -> Path | None:
    """Create backup of existing index.

    Args:
        vectors_dir: Path to vectors directory

    Returns:
        Backup path if backup was created, None otherwise
    """
    index_path = vectors_dir / "index.faiss"
    metadata_path = vectors_dir / "metadata.pkl"

    if not index_path.exists() or not metadata_path.exists():
        print("No existing index to backup")
        return None

    backup_dir = get_backup_path(vectors_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy(index_path, backup_dir / "index.faiss")
    shutil.copy(metadata_path, backup_dir / "metadata.pkl")

    print(f"Backed up existing index to: {backup_dir}")
    return backup_dir


def load_chunks(metadata_path: Path) -> list:
    """Load chunks from metadata file.

    Args:
        metadata_path: Path to metadata.pkl

    Returns:
        List of DocumentChunk objects
    """
    if not metadata_path.exists():
        print("No metadata file found")
        return []

    with open(metadata_path, "rb") as f:
        chunks = pickle.load(f)

    print(f"Loaded {len(chunks)} chunks from metadata")
    return chunks


def embed_chunks(chunks: list, embedding_service) -> np.ndarray:
    """Re-embed all chunks with new model.

    Args:
        chunks: List of DocumentChunk objects
        embedding_service: Embedding service to use

    Returns:
        Numpy array of embeddings
    """
    if not chunks:
        return np.array([])

    print(f"Embedding {len(chunks)} chunks with model: {embedding_service.model}")

    texts = [chunk.content for chunk in chunks]

    # Embed in batches to avoid memory issues
    batch_size = 100
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = embedding_service.embed_texts(batch)
        all_embeddings.extend(embeddings)
        print(f"  Processed {min(i + batch_size, len(texts))}/{len(texts)} chunks")

    return np.array(all_embeddings, dtype=np.float32)


def rebuild_index(embeddings: np.ndarray) -> faiss.IndexFlatIP:
    """Rebuild FAISS index from embeddings.

    Args:
        embeddings: Numpy array of embeddings

    Returns:
        New FAISS index
    """
    if len(embeddings) == 0:
        print("No embeddings to index")
        return None

    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    print(f"Built new index with {index.ntotal} vectors, dimension {dimension}")
    return index


def save_index(
    index: faiss.IndexFlatIP,
    chunks: list,
    vectors_dir: Path,
    embedding_model: str,
) -> None:
    """Save new index and metadata.

    Args:
        index: FAISS index
        chunks: List of DocumentChunk objects
        vectors_dir: Path to vectors directory
        embedding_model: Name of embedding model used
    """
    vectors_dir.mkdir(parents=True, exist_ok=True)

    index_path = vectors_dir / "index.faiss"
    metadata_path = vectors_dir / "metadata.pkl"
    model_path = vectors_dir / "embedding_model.txt"

    faiss.write_index(index, str(index_path))

    with open(metadata_path, "wb") as f:
        pickle.dump(chunks, f)

    # Store embedding model info for future compatibility checking
    with open(model_path, "w") as f:
        f.write(embedding_model)

    print(f"Saved new index to: {vectors_dir}")
    print(f"  - {index.ntotal} vectors")
    print(f"  - {len(chunks)} chunks")
    print(f"  - Embedding model: {embedding_model}")


def verify_integrity(vectors_dir: Path, expected_chunks: int) -> bool:
    """Verify the migrated index integrity.

    Args:
        vectors_dir: Path to vectors directory
        expected_chunks: Expected number of chunks

    Returns:
        True if verification passed
    """
    index_path = vectors_dir / "index.faiss"
    metadata_path = vectors_dir / "metadata.pkl"

    if not index_path.exists() or not metadata_path.exists():
        print("ERROR: Index or metadata file missing")
        return False

    index = faiss.read_index(str(index_path))

    with open(metadata_path, "rb") as f:
        chunks = pickle.load(f)

    if index.ntotal != expected_chunks:
        print(f"ERROR: Index has {index.ntotal} vectors, expected {expected_chunks}")
        return False

    if len(chunks) != expected_chunks:
        print(f"ERROR: Metadata has {len(chunks)} chunks, expected {expected_chunks}")
        return False

    print("Verification passed!")
    return True


def run_migration(
    vectors_dir: Path,
    new_model: str = "bge-m3",
    skip_backup: bool = False,
) -> bool:
    """Run the full migration process.

    Args:
        vectors_dir: Path to vectors directory
        new_model: New embedding model to use
        skip_backup: Skip creating backup

    Returns:
        True if migration succeeded
    """
    print(f"\n{'='*60}")
    print("Embedding Migration Script")
    print(f"{'='*60}")
    print(f"Vectors directory: {vectors_dir}")
    print(f"New embedding model: {new_model}")
    print()

    # Step 1: Backup
    if not skip_backup:
        backup_path = backup_index(vectors_dir)
        if backup_path:
            print(f"Backup created at: {backup_path}")
    else:
        print("Skipping backup (--skip-backup flag)")

    # Step 2: Load chunks
    metadata_path = vectors_dir / "metadata.pkl"
    chunks = load_chunks(metadata_path)

    if not chunks:
        print("No chunks to migrate")
        return True

    # Step 3: Re-embed with new model
    # Import here to avoid dependency issues when just showing help
    from ..config import get_settings
    from ..rag.embedding import EmbeddingService

    settings = get_settings()

    # Create embedding service with new model
    embedding_service = EmbeddingService(
        model=new_model,
        base_url=settings.ollama_base_url,
    )

    embeddings = embed_chunks(chunks, embedding_service)

    # Step 4: Rebuild index
    index = rebuild_index(embeddings)

    if index is None:
        print("Failed to build index")
        return False

    # Step 5: Save new index
    save_index(index, chunks, vectors_dir, new_model)

    # Step 6: Verify
    if verify_integrity(vectors_dir, len(chunks)):
        print(f"\n{'='*60}")
        print("Migration completed successfully!")
        print(f"{'='*60}\n")
        return True
    else:
        print("\nMigration verification failed!")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate embeddings to a new model")
    parser.add_argument(
        "--vectors-dir",
        type=Path,
        default=Path("data/vectors"),
        help="Path to vectors directory",
    )
    parser.add_argument(
        "--new-model",
        type=str,
        default="bge-m3",
        help="New embedding model to use",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip creating backup",
    )

    args = parser.parse_args()

    success = run_migration(
        vectors_dir=args.vectors_dir,
        new_model=args.new_model,
        skip_backup=args.skip_backup,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
