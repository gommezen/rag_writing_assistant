"""Retrieval confidence scoring for model routing.

Computes confidence metrics from retrieval results to determine
which LLM to use for generation - balancing speed vs quality.
"""

from ..config import get_settings
from ..core import get_logger
from ..models import (
    CoverageDescriptor,
    RetrievalConfidence,
    RetrievalConfidenceLevel,
    RetrievalConfidenceMetrics,
    SourceReference,
)

logger = get_logger(__name__)


class ConfidenceService:
    """Compute retrieval confidence for model routing."""

    # Threshold for considering a chunk "high quality"
    HIGH_QUALITY_THRESHOLD = 0.70

    def __init__(self):
        """Initialize confidence service."""
        self.settings = get_settings()

    def compute(
        self,
        sources: list[SourceReference],
        coverage: CoverageDescriptor,
    ) -> RetrievalConfidence:
        """Compute retrieval confidence from sources and coverage.

        This is used to route to different models:
        - HIGH: Strong relevance with multiple quality sources -> fast model
        - MEDIUM: Moderate relevance with at least one strong source -> standard model
        - LOW: Low relevance -> quality model with uncertainty prompts

        Args:
            sources: Retrieved source references with relevance scores
            coverage: Coverage descriptor from retrieval

        Returns:
            RetrievalConfidence with level, metrics, and suggested model
        """
        if not sources:
            return self._low_confidence("No sources retrieved")

        scores = [s.relevance_score for s in sources]
        avg_relevance = sum(scores) / len(scores)
        max_relevance = max(scores)
        high_quality_count = sum(
            1 for score in scores if score >= self.HIGH_QUALITY_THRESHOLD
        )

        # Compute source diversity (1 - max_doc_proportion)
        # Higher diversity = sources spread across more documents
        doc_counts: dict[str, int] = {}
        for source in sources:
            doc_counts[source.document_id] = doc_counts.get(source.document_id, 0) + 1
        max_proportion = max(doc_counts.values()) / len(sources)
        diversity = 1 - max_proportion

        metrics = RetrievalConfidenceMetrics(
            avg_relevance_score=avg_relevance,
            max_relevance_score=max_relevance,
            high_quality_chunk_count=high_quality_count,
            coverage_percentage=coverage.coverage_percentage,
            source_diversity=diversity,
        )

        # Decision logic for model routing
        # HIGH: avg >= 0.75 AND at least 3 high-quality chunks
        if avg_relevance >= 0.75 and high_quality_count >= 3:
            return RetrievalConfidence(
                level=RetrievalConfidenceLevel.HIGH,
                metrics=metrics,
                reasoning="Strong relevance with multiple high-quality sources",
                suggested_model=self.settings.fast_model,
            )

        # MEDIUM: avg >= 0.55 AND at least 1 high-quality chunk
        if avg_relevance >= 0.55 and high_quality_count >= 1:
            return RetrievalConfidence(
                level=RetrievalConfidenceLevel.MEDIUM,
                metrics=metrics,
                reasoning="Moderate relevance with at least one strong source",
                suggested_model=self.settings.standard_model,
            )

        # LOW: Everything else
        return RetrievalConfidence(
            level=RetrievalConfidenceLevel.LOW,
            metrics=metrics,
            reasoning="Low relevance - using quality model with uncertainty prompts",
            suggested_model=self.settings.quality_model,
        )

    def _low_confidence(self, reason: str) -> RetrievalConfidence:
        """Create a LOW confidence result with empty metrics."""
        metrics = RetrievalConfidenceMetrics(
            avg_relevance_score=0.0,
            max_relevance_score=0.0,
            high_quality_chunk_count=0,
            coverage_percentage=0.0,
            source_diversity=0.0,
        )
        return RetrievalConfidence(
            level=RetrievalConfidenceLevel.LOW,
            metrics=metrics,
            reasoning=reason,
            suggested_model=self.settings.quality_model,
        )


# Low confidence prompt suffix injected when retrieval quality is poor
LOW_CONFIDENCE_SUFFIX = """
IMPORTANT: Retrieved context has LOW relevance to this query.
- Be conservative in claims
- Explicitly state uncertainty
- Prefer "I don't have enough information" over speculation
- Only make statements directly supported by the provided sources
"""


# Singleton instance
_confidence_service: ConfidenceService | None = None


def get_confidence_service() -> ConfidenceService:
    """Get the singleton confidence service instance."""
    global _confidence_service
    if _confidence_service is None:
        _confidence_service = ConfidenceService()
    return _confidence_service
