"""Tests for validation service."""

from app.models import (
    ConfidenceLevel,
    GeneratedSection,
    SourceReference,
    WarningType,
)
from app.services.validation import ValidationService


class TestValidationService:
    """Tests for ValidationService."""

    def setup_method(self):
        self.service = ValidationService()

    def _create_source(
        self,
        doc_id: str = "doc-1",
        chunk_id: str = "chunk-1",
        score: float = 0.8,
    ) -> SourceReference:
        return SourceReference(
            document_id=doc_id,
            chunk_id=chunk_id,
            excerpt="Test excerpt",
            relevance_score=score,
        )

    def test_empty_sources_warns_insufficient_context(self):
        warnings = self.service.check_retrieval_quality([])

        assert len(warnings) > 0
        assert any(WarningType.INSUFFICIENT_CONTEXT in w for w in warnings)

    def test_few_sources_warns_insufficient_context(self):
        sources = [self._create_source(chunk_id=f"chunk-{i}") for i in range(2)]
        warnings = self.service.check_retrieval_quality(sources)

        assert any(WarningType.INSUFFICIENT_CONTEXT in w for w in warnings)

    def test_many_sources_no_insufficient_context_warning(self):
        sources = [self._create_source(chunk_id=f"chunk-{i}") for i in range(5)]
        warnings = self.service.check_retrieval_quality(sources)

        # Should not have insufficient context warning for 5 sources
        assert not any(
            WarningType.INSUFFICIENT_CONTEXT in w and "No relevant" in w for w in warnings
        )

    def test_low_relevance_warns(self):
        sources = [self._create_source(chunk_id=f"chunk-{i}", score=0.5) for i in range(5)]
        warnings = self.service.check_retrieval_quality(sources)

        assert any(WarningType.LOW_RELEVANCE_SOURCES in w for w in warnings)

    def test_high_relevance_no_warning(self):
        sources = [self._create_source(chunk_id=f"chunk-{i}", score=0.9) for i in range(5)]
        warnings = self.service.check_retrieval_quality(sources)

        assert not any(WarningType.LOW_RELEVANCE_SOURCES in w for w in warnings)

    def test_single_document_dominance_warns(self):
        # All 5 sources from same document
        sources = [self._create_source(doc_id="doc-1", chunk_id=f"chunk-{i}") for i in range(5)]
        warnings = self.service.check_retrieval_quality(sources)

        assert any(WarningType.SOURCE_OVER_RELIANCE in w for w in warnings)

    def test_diverse_documents_no_dominance_warning(self):
        sources = [self._create_source(doc_id=f"doc-{i}", chunk_id=f"chunk-{i}") for i in range(5)]
        warnings = self.service.check_retrieval_quality(sources)

        assert not any(WarningType.SOURCE_OVER_RELIANCE in w for w in warnings)


class TestSectionValidation:
    """Tests for section validation."""

    def setup_method(self):
        self.service = ValidationService()

    def test_no_sources_warns_potential_hallucination(self):
        section = GeneratedSection(
            section_id="sec-1",
            content="Some content",
            sources=[],  # No sources
            confidence=ConfidenceLevel.UNKNOWN,
        )

        warnings = self.service.validate_section(section, [])

        assert any(WarningType.POTENTIAL_HALLUCINATION in w for w in warnings)

    def test_low_confidence_warns(self):
        source = SourceReference(
            document_id="doc-1",
            chunk_id="chunk-1",
            excerpt="Test",
            relevance_score=0.8,
        )

        section = GeneratedSection(
            section_id="sec-1",
            content="Some content",
            sources=[source],
            confidence=ConfidenceLevel.LOW,
        )

        warnings = self.service.validate_section(section, [source])

        assert any(WarningType.INSUFFICIENT_CONTEXT in w for w in warnings)

    def test_uncertainty_markers_detected(self):
        source = SourceReference(
            document_id="doc-1",
            chunk_id="chunk-1",
            excerpt="Test",
            relevance_score=0.8,
        )

        section = GeneratedSection(
            section_id="sec-1",
            content="I don't have enough information to fully address this topic.",
            sources=[source],
            confidence=ConfidenceLevel.MEDIUM,
        )

        warnings = self.service.validate_section(section, [source])

        assert any(WarningType.INSUFFICIENT_CONTEXT in w for w in warnings)

    def test_high_confidence_with_sources_no_major_warnings(self):
        sources = [
            SourceReference(
                document_id=f"doc-{i}",
                chunk_id=f"chunk-{i}",
                excerpt="Test",
                relevance_score=0.9,
            )
            for i in range(3)
        ]

        section = GeneratedSection(
            section_id="sec-1",
            content="Well-supported content based on multiple sources.",
            sources=sources,
            confidence=ConfidenceLevel.HIGH,
        )

        warnings = self.service.validate_section(section, sources)

        # Should not have major warnings
        assert not any(WarningType.POTENTIAL_HALLUCINATION in w for w in warnings)
        assert not any(
            WarningType.INSUFFICIENT_CONTEXT in w and "Low confidence" in w for w in warnings
        )
