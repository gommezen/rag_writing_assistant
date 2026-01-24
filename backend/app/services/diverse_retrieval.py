"""Diverse retrieval service for analysis mode.

Samples chunks from different regions of documents to provide
representative coverage for summarization and analysis tasks.
"""

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
    RetrievalMetadata,
    RetrievalType,
    SourceReference,
)
from ..rag import get_vector_store

logger = get_logger(__name__)


# Region distribution for diverse sampling
# Intro (first 20%): 30% of samples - usually contains thesis/intro
# Middle (20-80%): 40% of samples - body content
# Conclusion (last 20%): 30% of samples - usually contains summary/conclusions
REGION_WEIGHTS = {
    DocumentRegion.INTRO: 0.30,
    DocumentRegion.MIDDLE: 0.40,
    DocumentRegion.CONCLUSION: 0.30,
}

# Region boundaries as percentage of document
REGION_BOUNDARIES = {
    DocumentRegion.INTRO: (0.0, 0.2),
    DocumentRegion.MIDDLE: (0.2, 0.8),
    DocumentRegion.CONCLUSION: (0.8, 1.0),
}


class DiverseRetrievalService:
    """Service for diverse document sampling."""

    def __init__(self):
        """Initialize diverse retrieval service."""
        self.settings = get_settings()
        self.vector_store = get_vector_store()

    def retrieve_diverse(
        self,
        document_ids: list[str] | None = None,
        target_chunks: int = 30,
        escalate: bool = False,
    ) -> tuple[list[SourceReference], RetrievalMetadata, CoverageDescriptor]:
        """Retrieve diverse samples from documents.

        Samples from intro, middle, and conclusion regions to provide
        representative coverage for analysis tasks.

        Args:
            document_ids: Optional filter by document IDs
            target_chunks: Target number of chunks to retrieve
            escalate: If True, increase sampling for more coverage

        Returns:
            Tuple of (sources, retrieval_metadata, coverage_descriptor)
        """
        start_time = time.time()

        # Escalation increases target chunks
        if escalate:
            target_chunks = min(target_chunks * 2, 60)

        # Get all chunks, optionally filtered by document
        all_chunks = self._get_filtered_chunks(document_ids)

        if not all_chunks:
            coverage = self._build_empty_coverage()
            metadata = self._build_metadata(
                query="diverse_sampling",
                chunks_retrieved=0,
                retrieval_time_ms=(time.time() - start_time) * 1000,
                coverage=coverage,
            )
            return [], metadata, coverage

        # Group chunks by document
        doc_chunks: dict[str, list[DocumentChunk]] = defaultdict(list)
        for chunk in all_chunks:
            doc_chunks[chunk.document_id].append(chunk)

        # Sort chunks within each document by chunk_index
        for doc_id in doc_chunks:
            doc_chunks[doc_id].sort(key=lambda c: c.chunk_index)

        # Sample from each document proportionally
        sampled_chunks = self._sample_diverse(doc_chunks, target_chunks)

        # Convert to SourceReferences
        sources = self._chunks_to_sources(sampled_chunks)

        # Compute coverage
        coverage = self._compute_coverage(
            sampled_chunks=sampled_chunks,
            all_chunks=doc_chunks,
        )

        retrieval_time_ms = (time.time() - start_time) * 1000

        metadata = self._build_metadata(
            query="diverse_sampling",
            chunks_retrieved=len(sources),
            retrieval_time_ms=retrieval_time_ms,
            coverage=coverage,
        )

        logger.info(
            "Diverse retrieval completed",
            documents_sampled=len(doc_chunks),
            chunks_retrieved=len(sources),
            coverage_percentage=round(coverage.coverage_percentage, 1),
            retrieval_time_ms=retrieval_time_ms,
        )

        return sources, metadata, coverage

    def _get_filtered_chunks(
        self,
        document_ids: list[str] | None,
    ) -> list[DocumentChunk]:
        """Get chunks, optionally filtered by document IDs."""
        chunks = self.vector_store.chunks

        if document_ids:
            chunks = [c for c in chunks if c.document_id in document_ids]

        return chunks

    def _sample_diverse(
        self,
        doc_chunks: dict[str, list[DocumentChunk]],
        target_chunks: int,
    ) -> list[DocumentChunk]:
        """Sample chunks from different regions of each document.

        Args:
            doc_chunks: Chunks grouped by document ID
            target_chunks: Total chunks to sample across all documents

        Returns:
            List of sampled chunks
        """
        num_docs = len(doc_chunks)
        if num_docs == 0:
            return []

        # Distribute chunks per document
        chunks_per_doc = max(3, target_chunks // num_docs)

        sampled = []

        for doc_id, chunks in doc_chunks.items():
            total_chunks = len(chunks)

            if total_chunks <= chunks_per_doc:
                # Document is small enough to include all chunks
                sampled.extend(chunks)
                continue

            # Calculate region boundaries for this document
            doc_samples = []
            for region, weight in REGION_WEIGHTS.items():
                region_samples = max(1, int(chunks_per_doc * weight))
                region_chunks = self._get_region_chunks(chunks, region)

                if region_chunks:
                    # Sample evenly from the region
                    step = max(1, len(region_chunks) // region_samples)
                    selected = region_chunks[::step][:region_samples]
                    doc_samples.extend(selected)

            sampled.extend(doc_samples)

        # Sort by document and chunk index for consistent ordering
        sampled.sort(key=lambda c: (c.document_id, c.chunk_index))

        return sampled[:target_chunks]

    def _get_region_chunks(
        self,
        chunks: list[DocumentChunk],
        region: DocumentRegion,
    ) -> list[DocumentChunk]:
        """Get chunks belonging to a specific region."""
        total = len(chunks)
        if total == 0:
            return []

        start_pct, end_pct = REGION_BOUNDARIES[region]
        start_idx = int(total * start_pct)
        end_idx = int(total * end_pct)

        # Ensure at least one chunk per region if document has enough chunks
        if start_idx == end_idx and total > 3:
            end_idx = start_idx + 1

        return chunks[start_idx:end_idx]

    def _chunks_to_sources(
        self,
        chunks: list[DocumentChunk],
    ) -> list[SourceReference]:
        """Convert DocumentChunks to SourceReferences."""
        sources = []
        for i, chunk in enumerate(chunks):
            # Use position-based relevance score for diverse sampling
            # Earlier chunks in each region get slightly higher scores
            relevance = 0.8 - (i * 0.01)  # Decreasing from 0.8
            relevance = max(relevance, 0.5)  # Floor at 0.5

            source = SourceReference(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                excerpt=self._truncate_excerpt(chunk.content),
                relevance_score=relevance,
                metadata=chunk.metadata,
            )
            sources.append(source)

        return sources

    def _truncate_excerpt(self, content: str, max_length: int = 200) -> str:
        """Truncate content for display as excerpt."""
        if len(content) <= max_length:
            return content
        return content[:max_length].rsplit(" ", 1)[0] + "..."

    def _compute_coverage(
        self,
        sampled_chunks: list[DocumentChunk],
        all_chunks: dict[str, list[DocumentChunk]],
    ) -> CoverageDescriptor:
        """Compute coverage descriptor for the sampling."""
        total_chunks = sum(len(chunks) for chunks in all_chunks.values())
        chunks_seen = len(sampled_chunks)

        # Group sampled chunks by document
        sampled_by_doc: dict[str, list[DocumentChunk]] = defaultdict(list)
        for chunk in sampled_chunks:
            sampled_by_doc[chunk.document_id].append(chunk)

        # Compute per-document coverage
        doc_coverage: dict[str, DocumentCoverage] = {}
        blind_spots: list[str] = []

        for doc_id, chunks in all_chunks.items():
            doc_sampled = sampled_by_doc.get(doc_id, [])
            doc_title = chunks[0].metadata.get("title", doc_id) if chunks else doc_id

            # Determine which regions were covered
            regions_covered = self._get_covered_regions(doc_sampled, len(chunks))
            all_regions = {DocumentRegion.INTRO, DocumentRegion.MIDDLE, DocumentRegion.CONCLUSION}
            regions_missing = list(all_regions - set(regions_covered))

            doc_cov = DocumentCoverage(
                document_id=doc_id,
                document_title=doc_title,
                chunks_seen=len(doc_sampled),
                chunks_total=len(chunks),
                regions_covered=regions_covered,
                regions_missing=regions_missing,
            )
            doc_coverage[doc_id] = doc_cov

            # Track blind spots
            if regions_missing:
                for region in regions_missing:
                    blind_spots.append(f"'{doc_title}': {region.value} section not sampled")

        # Compute overall coverage percentage
        coverage_pct = (chunks_seen / total_chunks * 100) if total_chunks > 0 else 0

        # Build coverage summary for prompt injection
        coverage_summary = self._build_coverage_summary(
            chunks_seen=chunks_seen,
            total_chunks=total_chunks,
            coverage_pct=coverage_pct,
            doc_coverage=doc_coverage,
        )

        return CoverageDescriptor(
            retrieval_type=RetrievalType.DIVERSE,
            chunks_seen=chunks_seen,
            chunks_total=total_chunks,
            coverage_percentage=coverage_pct,
            document_coverage=doc_coverage,
            blind_spots=blind_spots,
            coverage_summary=coverage_summary,
        )

    def _get_covered_regions(
        self,
        sampled: list[DocumentChunk],
        total_chunks: int,
    ) -> list[DocumentRegion]:
        """Determine which regions have coverage."""
        if total_chunks == 0:
            return []

        covered = set()
        for chunk in sampled:
            position = chunk.chunk_index / total_chunks
            if position < 0.2:
                covered.add(DocumentRegion.INTRO)
            elif position < 0.8:
                covered.add(DocumentRegion.MIDDLE)
            else:
                covered.add(DocumentRegion.CONCLUSION)

        return list(covered)

    def _build_coverage_summary(
        self,
        chunks_seen: int,
        total_chunks: int,
        coverage_pct: float,
        doc_coverage: dict[str, DocumentCoverage],
    ) -> str:
        """Build human-readable coverage summary for prompt injection."""
        num_docs = len(doc_coverage)

        summary_parts = [
            f"You are seeing {chunks_seen} of {total_chunks} total chunks "
            f"(~{coverage_pct:.0f}% of content) across {num_docs} document(s)."
        ]

        # Add confidence guidance based on coverage
        if coverage_pct < 15:
            summary_parts.append(
                "With less than 15% coverage, provide only exploratory observations. "
                "Use tentative language like 'may suggest', 'appears to indicate', 'based on limited view'."
            )
        elif coverage_pct < 40:
            summary_parts.append(
                "With moderate coverage, you can identify patterns but should note potential blind spots. "
                "Use language like 'the available content suggests', 'from what is visible'."
            )
        else:
            summary_parts.append(
                "With broader coverage, you can make more confident observations while still citing sources."
            )

        return " ".join(summary_parts)

    def _build_empty_coverage(self) -> CoverageDescriptor:
        """Build coverage descriptor for empty results."""
        return CoverageDescriptor(
            retrieval_type=RetrievalType.DIVERSE,
            chunks_seen=0,
            chunks_total=0,
            coverage_percentage=0,
            document_coverage={},
            blind_spots=["No documents available for analysis"],
            coverage_summary="No documents are available. Cannot provide analysis.",
        )

    def _build_metadata(
        self,
        query: str,
        chunks_retrieved: int,
        retrieval_time_ms: float,
        coverage: CoverageDescriptor,
    ) -> RetrievalMetadata:
        """Build retrieval metadata for diverse sampling."""
        return RetrievalMetadata(
            query=query,
            top_k=chunks_retrieved,  # For diverse, top_k equals actual retrieved
            similarity_threshold=0.0,  # Not applicable for diverse sampling
            chunks_retrieved=chunks_retrieved,
            chunks_above_threshold=chunks_retrieved,
            retrieval_time_ms=retrieval_time_ms,
            timestamp=datetime.now(UTC),
            retrieval_type=RetrievalType.DIVERSE,
            coverage=coverage,
        )


# Singleton instance
_diverse_retrieval_service: DiverseRetrievalService | None = None


def get_diverse_retrieval_service() -> DiverseRetrievalService:
    """Get the singleton diverse retrieval service instance."""
    global _diverse_retrieval_service
    if _diverse_retrieval_service is None:
        _diverse_retrieval_service = DiverseRetrievalService()
    return _diverse_retrieval_service
