"""Validation service for generated content.

Detects potential issues like insufficient context, over-reliance on
single sources, and unsupported claims.
"""

from ..core import get_logger
from ..models import ConfidenceLevel, GeneratedSection, SourceReference, WarningType

logger = get_logger(__name__)


class ValidationService:
    """Service for validating retrieval and generation quality."""

    # Thresholds for validation
    MIN_SOURCES_FOR_HIGH_CONFIDENCE = 3
    MIN_RELEVANCE_SCORE = 0.7
    MAX_SINGLE_SOURCE_RELIANCE = 0.7  # Don't rely on one source for >70% of content

    def check_retrieval_quality(
        self,
        sources: list[SourceReference],
    ) -> list[str]:
        """Check quality of retrieved sources.

        Args:
            sources: List of retrieved source references

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for insufficient sources
        if len(sources) == 0:
            warnings.append(
                f"{WarningType.INSUFFICIENT_CONTEXT}: No relevant sources found. "
                "Generated content may not be well-supported."
            )
        elif len(sources) < self.MIN_SOURCES_FOR_HIGH_CONFIDENCE:
            warnings.append(
                f"{WarningType.INSUFFICIENT_CONTEXT}: Only {len(sources)} source(s) found. "
                "Consider adding more relevant documents."
            )

        # Check for low relevance scores
        if sources:
            avg_relevance = sum(s.relevance_score for s in sources) / len(sources)
            if avg_relevance < self.MIN_RELEVANCE_SCORE:
                warnings.append(
                    f"{WarningType.LOW_RELEVANCE_SOURCES}: Average source relevance is low "
                    f"({avg_relevance:.2f}). Content may not closely match the topic."
                )

        # Check for single-document dominance
        if sources:
            doc_counts: dict[str, int] = {}
            for source in sources:
                doc_counts[source.document_id] = doc_counts.get(source.document_id, 0) + 1

            for doc_id, count in doc_counts.items():
                if count / len(sources) > self.MAX_SINGLE_SOURCE_RELIANCE:
                    warnings.append(
                        f"{WarningType.SOURCE_OVER_RELIANCE}: Over-reliance on single document. "
                        "Consider diversifying sources."
                    )
                    break

        return warnings

    def validate_section(
        self,
        section: GeneratedSection,
        available_sources: list[SourceReference],
    ) -> list[str]:
        """Validate a generated section.

        Args:
            section: Generated section to validate
            available_sources: All available source references

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for missing citations
        if not section.sources:
            warnings.append(
                f"{WarningType.POTENTIAL_HALLUCINATION}: No sources cited for this section. "
                "Content may contain unsupported claims."
            )

        # Check confidence level
        if section.confidence == ConfidenceLevel.LOW:
            warnings.append(
                f"{WarningType.INSUFFICIENT_CONTEXT}: Low confidence section. "
                "Review and verify claims manually."
            )
        elif section.confidence == ConfidenceLevel.UNKNOWN:
            warnings.append(
                f"{WarningType.POTENTIAL_HALLUCINATION}: Could not determine confidence level. "
                "Citations may be missing."
            )

        # Check for over-reliance on single source within section
        if len(section.sources) == 1 and len(available_sources) > 3:
            warnings.append(
                f"{WarningType.SOURCE_OVER_RELIANCE}: Section relies on single source "
                "despite multiple being available."
            )

        # Check for explicit uncertainty in content
        uncertainty_phrases = [
            "i don't have enough information",
            "insufficient context",
            "cannot find support",
            "no relevant sources found",
            "unable to verify",
        ]

        content_lower = section.content.lower()
        for phrase in uncertainty_phrases:
            if phrase in content_lower:
                warnings.append(
                    f"{WarningType.INSUFFICIENT_CONTEXT}: Content indicates insufficient "
                    "information to fully address the topic."
                )
                break

        return warnings

    def check_source_coverage(
        self,
        sections: list[GeneratedSection],
        all_sources: list[SourceReference],
    ) -> dict[str, bool]:
        """Check which sources were used across all sections.

        Args:
            sections: List of generated sections
            all_sources: All available sources

        Returns:
            Dict mapping source chunk_id to whether it was used
        """
        used_chunk_ids = set()
        for section in sections:
            for source in section.sources:
                used_chunk_ids.add(source.chunk_id)

        return {
            source.chunk_id: source.chunk_id in used_chunk_ids
            for source in all_sources
        }


# Singleton instance
_validation_service: ValidationService | None = None


def get_validation_service() -> ValidationService:
    """Get the singleton validation service instance."""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service
