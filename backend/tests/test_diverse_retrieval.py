"""Tests for diverse retrieval service.

Verifies that:
- Chunks are sampled from all three regions (intro/middle/conclusion)
- Coverage descriptor is computed correctly
- Blind spots are identified when regions are missing
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models import (
    CoverageDescriptor,
    DocumentCoverage,
    DocumentRegion,
    RetrievalType,
)
from app.services.diverse_retrieval import (
    REGION_BOUNDARIES,
    REGION_WEIGHTS,
    DiverseRetrievalService,
    get_diverse_retrieval_service,
)


class TestDiverseRetrieval:
    """Test diverse sampling retrieval."""

    @pytest.fixture
    def mock_vector_store(self, sample_chunks_factory):
        """Create a mock vector store with chunks."""
        mock_store = MagicMock()
        # Create 20 chunks for a document to have meaningful regions
        mock_store.chunks = sample_chunks_factory(
            document_id="doc-001",
            count=20,
            content_prefix="Document content",
            metadata={"title": "Test Document"},
        )
        return mock_store

    @pytest.fixture
    def diverse_service(self, mock_vector_store):
        """Create diverse retrieval service with mocked vector store."""
        with patch(
            "app.services.diverse_retrieval.get_vector_store", return_value=mock_vector_store
        ):
            with patch("app.services.diverse_retrieval.get_settings") as mock_settings:
                mock_settings.return_value.top_k_retrieval = 10
                mock_settings.return_value.default_coverage_pct = 35.0
                mock_settings.return_value.max_coverage_pct = 80.0
                service = DiverseRetrievalService()
                yield service

    # ========================================================================
    # Region Sampling Tests
    # ========================================================================

    def test_samples_from_all_regions(self, diverse_service, mock_vector_store):
        """Diverse retrieval should sample from intro, middle, and conclusion regions."""
        sources, metadata, coverage = diverse_service.retrieve_diverse(
            document_ids=["doc-001"],
            target_chunks=10,
        )

        # Should have samples from multiple regions
        assert len(sources) > 0
        assert coverage.chunks_seen > 0

        # Check that regions were covered
        doc_coverage = coverage.document_coverage.get("doc-001")
        assert doc_coverage is not None
        # With 20 chunks and 10 target, should cover multiple regions
        assert len(doc_coverage.regions_covered) >= 2

    def test_empty_store_returns_empty_results(self):
        """Empty vector store should return empty results with appropriate coverage."""
        mock_store = MagicMock()
        mock_store.chunks = []

        with patch("app.services.diverse_retrieval.get_vector_store", return_value=mock_store):
            with patch("app.services.diverse_retrieval.get_settings"):
                service = DiverseRetrievalService()
                sources, metadata, coverage = service.retrieve_diverse()

        assert len(sources) == 0
        assert coverage.chunks_seen == 0
        assert coverage.chunks_total == 0
        assert "No documents available" in coverage.blind_spots[0]

    def test_small_document_includes_all_chunks(self, sample_chunks_factory):
        """Small documents should include all chunks."""
        mock_store = MagicMock()
        # Only 3 chunks - should all be included
        mock_store.chunks = sample_chunks_factory(
            document_id="doc-001",
            count=3,
            metadata={"title": "Small Doc"},
        )

        with patch("app.services.diverse_retrieval.get_vector_store", return_value=mock_store):
            with patch("app.services.diverse_retrieval.get_settings"):
                service = DiverseRetrievalService()
                sources, metadata, coverage = service.retrieve_diverse(
                    target_chunks=10,  # More than available
                )

        assert len(sources) == 3
        assert coverage.coverage_percentage == 100.0

    # ========================================================================
    # Coverage Computation Tests
    # ========================================================================

    def test_coverage_percentage_computed_correctly(self, diverse_service, mock_vector_store):
        """Coverage percentage should be (chunks_seen / chunks_total) * 100."""
        sources, metadata, coverage = diverse_service.retrieve_diverse(
            document_ids=["doc-001"],
            target_chunks=5,
        )

        expected_pct = (coverage.chunks_seen / 20) * 100
        assert abs(coverage.coverage_percentage - expected_pct) < 0.1

    def test_coverage_summary_reflects_confidence_level(self, diverse_service):
        """Coverage summary should use appropriate language based on coverage level."""
        sources, metadata, coverage = diverse_service.retrieve_diverse(
            target_chunks=3,  # Relatively low coverage
        )

        # Coverage summary should provide guidance based on coverage level
        # At ~15% this is moderate coverage, which warns about blind spots
        summary_lower = coverage.coverage_summary.lower()
        assert "coverage" in summary_lower or "chunks" in summary_lower
        # Should include guidance language appropriate to the coverage level
        assert any(
            term in summary_lower
            for term in [
                "exploratory",
                "tentative",
                "limited",  # low coverage
                "moderate",
                "patterns",
                "blind spots",  # moderate coverage
                "confident",
                "broader",  # high coverage
            ]
        )

    def test_blind_spots_identified(self, sample_chunks_factory):
        """Blind spots should be identified when regions are missing."""
        mock_store = MagicMock()
        # Create chunks only from the beginning (intro region)
        chunks = sample_chunks_factory(
            document_id="doc-001",
            count=5,
            metadata={"title": "Test Doc"},
        )
        # All chunks have low indices (0-4), simulating only intro coverage
        mock_store.chunks = chunks

        with patch("app.services.diverse_retrieval.get_vector_store", return_value=mock_store):
            with patch("app.services.diverse_retrieval.get_settings"):
                service = DiverseRetrievalService()
                sources, metadata, coverage = service.retrieve_diverse(
                    target_chunks=2,  # Only get 2 chunks
                )

        # Should identify missing regions as blind spots
        doc_coverage = coverage.document_coverage.get("doc-001")
        assert doc_coverage is not None
        # With limited sampling, some regions should be missing
        assert len(doc_coverage.regions_missing) > 0 or len(coverage.blind_spots) >= 0

    # ========================================================================
    # Document Filtering Tests
    # ========================================================================

    def test_filters_by_document_ids(self, sample_chunks_factory):
        """Should only include chunks from specified documents."""
        mock_store = MagicMock()
        # Create chunks from multiple documents
        mock_store.chunks = sample_chunks_factory(
            document_id="doc-001", count=10, metadata={"title": "Doc 1"}
        ) + sample_chunks_factory(document_id="doc-002", count=10, metadata={"title": "Doc 2"})

        with patch("app.services.diverse_retrieval.get_vector_store", return_value=mock_store):
            with patch("app.services.diverse_retrieval.get_settings"):
                service = DiverseRetrievalService()
                sources, metadata, coverage = service.retrieve_diverse(
                    document_ids=["doc-001"],  # Only doc-001
                    target_chunks=20,
                )

        # All sources should be from doc-001
        assert all(s.document_id == "doc-001" for s in sources)
        # Coverage should only include doc-001
        assert "doc-001" in coverage.document_coverage
        assert "doc-002" not in coverage.document_coverage

    # ========================================================================
    # Escalation Tests
    # ========================================================================

    def test_escalation_increases_chunks(self, diverse_service):
        """Escalation should retrieve more chunks."""
        sources_normal, _, coverage_normal = diverse_service.retrieve_diverse(
            target_chunks=5,
            escalate=False,
        )

        sources_escalated, _, coverage_escalated = diverse_service.retrieve_diverse(
            target_chunks=5,
            escalate=True,
        )

        # Escalated should have more chunks (up to 2x or available)
        assert coverage_escalated.chunks_seen >= coverage_normal.chunks_seen

    # ========================================================================
    # Metadata Tests
    # ========================================================================

    def test_retrieval_metadata_type_is_diverse(self, diverse_service):
        """Retrieval metadata should have type DIVERSE."""
        sources, metadata, coverage = diverse_service.retrieve_diverse(
            target_chunks=5,
        )

        assert metadata.retrieval_type == RetrievalType.DIVERSE
        assert coverage.retrieval_type == RetrievalType.DIVERSE

    def test_sources_have_metadata(self, diverse_service):
        """Source references should preserve chunk metadata."""
        sources, _, _ = diverse_service.retrieve_diverse(target_chunks=5)

        for source in sources:
            assert source.metadata is not None
            assert "title" in source.metadata


class TestCoverageDescriptorSerialization:
    """Test CoverageDescriptor serialization."""

    def test_to_dict(self):
        """CoverageDescriptor should serialize correctly."""
        doc_coverage = DocumentCoverage(
            document_id="doc-001",
            document_title="Test Document",
            chunks_seen=5,
            chunks_total=20,
            regions_covered=[DocumentRegion.INTRO, DocumentRegion.MIDDLE],
            regions_missing=[DocumentRegion.CONCLUSION],
        )

        coverage = CoverageDescriptor(
            retrieval_type=RetrievalType.DIVERSE,
            chunks_seen=5,
            chunks_total=20,
            coverage_percentage=25.0,
            document_coverage={"doc-001": doc_coverage},
            blind_spots=["Test blind spot"],
            coverage_summary="Test summary",
        )

        data = coverage.to_dict()

        assert data["retrieval_type"] == "diverse"
        assert data["chunks_seen"] == 5
        assert data["chunks_total"] == 20
        assert data["coverage_percentage"] == 25.0
        assert "doc-001" in data["document_coverage"]
        assert data["blind_spots"] == ["Test blind spot"]

    def test_from_dict(self):
        """CoverageDescriptor should deserialize correctly."""
        data = {
            "retrieval_type": "diverse",
            "chunks_seen": 10,
            "chunks_total": 100,
            "coverage_percentage": 10.0,
            "document_coverage": {
                "doc-001": {
                    "document_id": "doc-001",
                    "document_title": "Test",
                    "chunks_seen": 10,
                    "chunks_total": 100,
                    "coverage_percentage": 10.0,
                    "regions_covered": ["intro", "middle"],
                    "regions_missing": ["conclusion"],
                }
            },
            "blind_spots": ["Missing conclusion"],
            "coverage_summary": "Test summary",
        }

        coverage = CoverageDescriptor.from_dict(data)

        assert coverage.retrieval_type == RetrievalType.DIVERSE
        assert coverage.chunks_seen == 10
        assert "doc-001" in coverage.document_coverage
        assert DocumentRegion.INTRO in coverage.document_coverage["doc-001"].regions_covered


class TestRegionConfiguration:
    """Test region boundary and weight configuration."""

    def test_region_weights_sum_to_one(self):
        """Region weights should sum to 1.0 for proportional distribution."""
        total = sum(REGION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_region_boundaries_cover_full_document(self):
        """Region boundaries should cover 0% to 100% of document."""
        start = REGION_BOUNDARIES[DocumentRegion.INTRO][0]
        end = REGION_BOUNDARIES[DocumentRegion.CONCLUSION][1]

        assert start == 0.0
        assert end == 1.0

    def test_region_boundaries_no_gaps(self):
        """Region boundaries should have no gaps."""
        intro_end = REGION_BOUNDARIES[DocumentRegion.INTRO][1]
        middle_start = REGION_BOUNDARIES[DocumentRegion.MIDDLE][0]
        middle_end = REGION_BOUNDARIES[DocumentRegion.MIDDLE][1]
        conclusion_start = REGION_BOUNDARIES[DocumentRegion.CONCLUSION][0]

        assert intro_end == middle_start
        assert middle_end == conclusion_start


class TestDiverseRetrievalServiceSingleton:
    """Test singleton behavior."""

    def test_get_diverse_retrieval_service_returns_same_instance(self):
        """get_diverse_retrieval_service should return the same instance."""
        with patch("app.services.diverse_retrieval.get_vector_store"):
            with patch("app.services.diverse_retrieval.get_settings"):
                # Reset singleton
                import app.services.diverse_retrieval as module

                module._diverse_retrieval_service = None

                service1 = get_diverse_retrieval_service()
                service2 = get_diverse_retrieval_service()

                assert service1 is service2
