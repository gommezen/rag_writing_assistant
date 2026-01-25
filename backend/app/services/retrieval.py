"""Retrieval service for searching document chunks.

Provides similarity search with threshold filtering and metadata tracking.
"""

import math
import time
from collections import defaultdict
from datetime import UTC, datetime

from ..config import get_settings
from ..core import get_logger
from ..models import (
    CoverageDescriptor,
    DocumentChunk,
    DocumentCoverage,
    DocumentRegion,
    QueryIntent,
    RetrievalMetadata,
    RetrievalType,
    SourceReference,
)
from ..rag import get_vector_store
from .reranker import get_reranker_service

logger = get_logger(__name__)


class RetrievalService:
    """Service for retrieving relevant document chunks."""

    def __init__(self):
        """Initialize retrieval service."""
        self.settings = get_settings()
        self.vector_store = get_vector_store()
        self._reranker = None

    @property
    def reranker(self):
        """Lazy-load reranker service."""
        if self._reranker is None and self.settings.reranker_enabled:
            self._reranker = get_reranker_service()
        return self._reranker

    def _get_threshold_for_intent(self, intent: QueryIntent | None) -> float:
        """Select similarity threshold based on query intent.

        Different intents have different precision/recall trade-offs:
        - QA: High threshold (0.50) for precise matches
        - ANALYSIS: Low threshold (0.25) for broad coverage
        - WRITING: Balanced threshold (0.35)
        """
        if intent == QueryIntent.QA:
            return self.settings.qa_similarity_threshold
        elif intent == QueryIntent.ANALYSIS:
            return self.settings.analysis_similarity_threshold
        elif intent == QueryIntent.WRITING:
            return self.settings.writing_similarity_threshold
        return self.settings.similarity_threshold

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
        document_ids: list[str] | None = None,
        intent: QueryIntent | None = None,
        use_reranker: bool | None = None,
    ) -> tuple[list[SourceReference], RetrievalMetadata]:
        """Retrieve relevant chunks for a query.

        Args:
            query: Search query
            top_k: Number of results to return
            threshold: Minimum similarity threshold (uses intent-specific if not provided)
            document_ids: Optional filter by document IDs
            intent: Query intent for threshold selection
            use_reranker: Override reranker setting (defaults to config)

        Returns:
            Tuple of (source references, retrieval metadata)
        """
        top_k = top_k or self.settings.top_k_retrieval

        # Use intent-specific threshold if not explicitly provided
        if threshold is None:
            threshold = self._get_threshold_for_intent(intent)

        # Determine if reranking is enabled
        reranker_enabled = use_reranker if use_reranker is not None else self.settings.reranker_enabled

        start_time = time.time()

        # If reranking, retrieve more candidates initially
        initial_k = self.settings.reranker_initial_k if reranker_enabled else top_k

        # Search vector store with lower threshold for reranking
        search_threshold = threshold * 0.5 if reranker_enabled else threshold
        results = self.vector_store.search(
            query=query,
            top_k=initial_k,
            threshold=search_threshold,
            document_ids=document_ids,
        )

        reranker_used = False

        # Apply reranking if enabled and we have results
        if reranker_enabled and self.reranker and results:
            reranker_used = True
            reranked = self.reranker.rerank(
                query=query,
                chunks=results,
                top_k=top_k,
            )
            # Convert rerank scores to 0-1 range using sigmoid for consistency
            # Cross-encoder scores are logits (can be negative), not probabilities
            results = [
                (chunk, 1 / (1 + math.exp(-rerank_score)))  # sigmoid normalization
                for chunk, _, rerank_score in reranked
            ]
            # Note: Don't filter by threshold after reranking - the reranker has already
            # selected top-k by relevance. Threshold filtering is for FAISS scores only.

        retrieval_time_ms = (time.time() - start_time) * 1000

        # Convert to SourceReferences
        sources = []
        for chunk, score in results:
            source = SourceReference(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                excerpt=self._truncate_excerpt(chunk.content),
                relevance_score=score,
                metadata=chunk.metadata,
            )
            sources.append(source)

        # Build metadata
        metadata = RetrievalMetadata(
            query=query,
            top_k=top_k,
            similarity_threshold=threshold,
            chunks_retrieved=len(results),
            chunks_above_threshold=len([r for r in results if r[1] >= threshold]),
            retrieval_time_ms=retrieval_time_ms,
            timestamp=datetime.now(UTC),
        )

        logger.info(
            "Retrieval completed",
            query_length=len(query),
            results_count=len(sources),
            top_k=top_k,
            threshold=threshold,
            retrieval_time_ms=retrieval_time_ms,
            intent=intent.value if intent else None,
            reranker_used=reranker_used,
        )

        return sources, metadata

    def retrieve_for_sources(
        self,
        query: str,
        document_ids: list[str] | None = None,
    ) -> list[dict]:
        """Retrieve chunks formatted for prompt context.

        This is a convenience method that returns chunks in the format
        expected by the prompt templates.

        Args:
            query: Search query
            document_ids: Optional filter by document IDs

        Returns:
            List of dicts with 'content' and 'metadata' keys
        """
        sources, _ = self.retrieve(query=query, document_ids=document_ids)

        return [
            {
                "content": self._get_full_content(source),
                "metadata": source.metadata,
            }
            for source in sources
        ]

    def _truncate_excerpt(self, content: str, max_length: int = 200) -> str:
        """Truncate content for display as excerpt."""
        if len(content) <= max_length:
            return content
        return content[:max_length].rsplit(" ", 1)[0] + "..."

    def _get_full_content(self, source: SourceReference) -> str:
        """Get full chunk content from vector store.

        Note: The excerpt is truncated, so we need to get the full content
        from the original chunk for prompt building.
        """
        # Search the vector store's chunks for the matching chunk_id
        for chunk in self.vector_store.chunks:
            if chunk.chunk_id == source.chunk_id:
                return chunk.content
        return source.excerpt  # Fallback to excerpt if not found

    def compute_similarity_coverage(
        self,
        sources: list[SourceReference],
        document_ids: list[str] | None = None,
    ) -> CoverageDescriptor:
        """Compute coverage descriptor for similarity-based retrieval.

        Coverage is computed AFTER retrieval to describe what portion
        of the available documents was actually seen.

        Args:
            sources: Retrieved source references
            document_ids: Optional filter by document IDs

        Returns:
            CoverageDescriptor describing the retrieval coverage
        """
        # Get all chunks for coverage calculation
        all_chunks = self.vector_store.chunks
        if document_ids:
            all_chunks = [c for c in all_chunks if c.document_id in document_ids]

        if not all_chunks:
            return CoverageDescriptor(
                retrieval_type=RetrievalType.SIMILARITY,
                chunks_seen=0,
                chunks_total=0,
                coverage_percentage=0,
                document_coverage={},
                blind_spots=["No documents available"],
                coverage_summary="No documents are available for retrieval.",
            )

        # Group all chunks by document
        all_by_doc: dict[str, list[DocumentChunk]] = defaultdict(list)
        for chunk in all_chunks:
            all_by_doc[chunk.document_id].append(chunk)

        # Get chunk IDs from sources
        source_chunk_ids = {s.chunk_id for s in sources}

        # Group retrieved chunks by document
        retrieved_by_doc: dict[str, int] = defaultdict(int)
        for source in sources:
            retrieved_by_doc[source.document_id] += 1

        # Compute per-document coverage
        doc_coverage: dict[str, DocumentCoverage] = {}
        blind_spots: list[str] = []

        for doc_id, chunks in all_by_doc.items():
            chunks.sort(key=lambda c: c.chunk_index)
            doc_title = chunks[0].metadata.get("title", doc_id) if chunks else doc_id
            chunks_seen = retrieved_by_doc.get(doc_id, 0)

            # Determine covered regions based on retrieved chunks
            regions_covered = []
            for chunk in chunks:
                if chunk.chunk_id in source_chunk_ids:
                    total = len(chunks)
                    position = chunk.chunk_index / total if total > 0 else 0
                    if position < 0.2:
                        regions_covered.append(DocumentRegion.INTRO)
                    elif position < 0.8:
                        regions_covered.append(DocumentRegion.MIDDLE)
                    else:
                        regions_covered.append(DocumentRegion.CONCLUSION)

            regions_covered = list(set(regions_covered))
            all_regions = {DocumentRegion.INTRO, DocumentRegion.MIDDLE, DocumentRegion.CONCLUSION}
            regions_missing = list(all_regions - set(regions_covered))

            doc_cov = DocumentCoverage(
                document_id=doc_id,
                document_title=doc_title,
                chunks_seen=chunks_seen,
                chunks_total=len(chunks),
                regions_covered=regions_covered,
                regions_missing=regions_missing,
            )
            doc_coverage[doc_id] = doc_cov

            # Track blind spots for documents with no coverage
            if chunks_seen == 0:
                blind_spots.append(f"'{doc_title}': no chunks retrieved")

        # Compute overall coverage
        total_chunks = len(all_chunks)
        chunks_seen = len(sources)
        coverage_pct = (chunks_seen / total_chunks * 100) if total_chunks > 0 else 0

        # Build coverage summary
        coverage_summary = self._build_similarity_coverage_summary(
            chunks_seen=chunks_seen,
            total_chunks=total_chunks,
            coverage_pct=coverage_pct,
            doc_count=len(doc_coverage),
        )

        return CoverageDescriptor(
            retrieval_type=RetrievalType.SIMILARITY,
            chunks_seen=chunks_seen,
            chunks_total=total_chunks,
            coverage_percentage=coverage_pct,
            document_coverage=doc_coverage,
            blind_spots=blind_spots,
            coverage_summary=coverage_summary,
        )

    def _build_similarity_coverage_summary(
        self,
        chunks_seen: int,
        total_chunks: int,
        coverage_pct: float,
        doc_count: int,
    ) -> str:
        """Build human-readable coverage summary for similarity retrieval."""
        summary_parts = [
            f"Retrieved {chunks_seen} most relevant chunks from {total_chunks} total "
            f"(~{coverage_pct:.0f}% of content) across {doc_count} document(s)."
        ]

        if coverage_pct < 10:
            summary_parts.append(
                "This is a focused retrieval of the most relevant content. "
                "Claims should be limited to what these specific sources support."
            )
        else:
            summary_parts.append(
                "Use the retrieved context to ground your response, citing sources."
            )

        return " ".join(summary_parts)


# Singleton instance
_retrieval_service: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    """Get the singleton retrieval service instance."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
