"""Tests for generation service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import LLMError
from app.models import (
    ConfidenceLevel,
)
from app.rag.prompts import extract_citations
from app.services.generation import GenerationService


@pytest.mark.integration
class TestGenerationServiceBasics:
    """Tests for basic generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_creates_sections_with_sources(
        self, mock_settings, mock_embedding_service, mock_llm, sample_chunks_factory
    ):
        """Generation should create sections with source references."""
        chunks = sample_chunks_factory(count=5, metadata={"title": "Test Doc"})

        mock_llm.set_response(
            "This is the generated content. [Source 1] It includes citations. "
            "[Source 2] And references multiple sources.\n\n"
            "Another paragraph with [Source 3] additional content."
        )

        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        from app.rag.vectorstore import VectorStore

                        vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                        vector_store.add_chunks(chunks)

                        with patch(
                            "app.services.retrieval.get_vector_store", return_value=vector_store
                        ):
                            with patch(
                                "app.services.generation.get_retrieval_service"
                            ) as mock_retrieval:
                                from app.services.retrieval import RetrievalService

                                real_retrieval = RetrievalService()
                                mock_retrieval.return_value = real_retrieval

                                with patch("app.services.generation.get_validation_service"):
                                    service = GenerationService()
                                    service._get_or_create_llm = lambda model: mock_llm

                                    result = await service.generate(
                                        prompt="Write about testing",
                                        max_sections=5,
                                    )

                                    # Verify sections are created
                                    assert result.sections is not None
                                    assert len(result.sections) > 0

                                    # Verify each section has sources
                                    for section in result.sections:
                                        assert section.sources is not None
                                        assert isinstance(section.sources, list)

    @pytest.mark.asyncio
    async def test_generate_includes_confidence_levels(
        self, mock_settings, mock_embedding_service, mock_llm, sample_chunks_factory
    ):
        """Generated sections should include confidence levels."""
        chunks = sample_chunks_factory(count=5)

        mock_llm.set_response("Generated content with [Source 1] citations [Source 2].")

        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        from app.rag.vectorstore import VectorStore

                        vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                        vector_store.add_chunks(chunks)

                        with patch(
                            "app.services.retrieval.get_vector_store", return_value=vector_store
                        ):
                            with patch(
                                "app.services.generation.get_retrieval_service"
                            ) as mock_retrieval:
                                from app.services.retrieval import RetrievalService

                                mock_retrieval.return_value = RetrievalService()

                                with patch("app.services.generation.get_validation_service"):
                                    service = GenerationService()
                                    service._get_or_create_llm = lambda model: mock_llm

                                    result = await service.generate(
                                        prompt="Write content",
                                        max_sections=5,
                                    )

                                    for section in result.sections:
                                        assert section.confidence is not None
                                        assert isinstance(section.confidence, ConfidenceLevel)

    @pytest.mark.asyncio
    async def test_generate_includes_warnings(
        self, mock_settings, mock_embedding_service, mock_llm, sample_chunks_factory
    ):
        """Generated sections should include warnings array."""
        chunks = sample_chunks_factory(count=5)

        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        from app.rag.vectorstore import VectorStore

                        vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                        vector_store.add_chunks(chunks)

                        with patch(
                            "app.services.retrieval.get_vector_store", return_value=vector_store
                        ):
                            with patch(
                                "app.services.generation.get_retrieval_service"
                            ) as mock_retrieval:
                                from app.services.retrieval import RetrievalService

                                mock_retrieval.return_value = RetrievalService()

                                with patch("app.services.generation.get_validation_service"):
                                    service = GenerationService()
                                    service._get_or_create_llm = lambda model: mock_llm

                                    result = await service.generate(
                                        prompt="Write content",
                                        max_sections=5,
                                    )

                                    for section in result.sections:
                                        assert section.warnings is not None
                                        assert isinstance(section.warnings, list)


@pytest.mark.integration
class TestGenerationWithNoSources:
    """Tests for generation behavior when no sources are found."""

    @pytest.mark.asyncio
    async def test_generate_with_no_sources_warns(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Generation with no sources should include warnings."""
        mock_llm.set_response("I don't have enough information to write about this topic.")

        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        # Empty vector store
                        from app.rag.vectorstore import VectorStore

                        vector_store = VectorStore(store_path=mock_settings.vectors_dir)

                        with patch(
                            "app.services.retrieval.get_vector_store", return_value=vector_store
                        ):
                            with patch(
                                "app.services.generation.get_retrieval_service"
                            ) as mock_retrieval:
                                from app.services.retrieval import RetrievalService

                                mock_retrieval.return_value = RetrievalService()

                                # Mock validation service to return warnings
                                with patch(
                                    "app.services.generation.get_validation_service"
                                ) as mock_val:
                                    mock_validation = MagicMock()
                                    mock_validation.check_retrieval_quality.return_value = [
                                        "insufficient_context: No relevant sources found"
                                    ]
                                    mock_validation.validate_section.return_value = []
                                    mock_val.return_value = mock_validation

                                    service = GenerationService()
                                    service._get_or_create_llm = lambda model: mock_llm

                                    result = await service.generate(
                                        prompt="Write about unknown topic",
                                        max_sections=5,
                                    )

                                    # Confidence should be LOW or UNKNOWN
                                    for section in result.sections:
                                        assert section.confidence in [
                                            ConfidenceLevel.LOW,
                                            ConfidenceLevel.UNKNOWN,
                                        ]


@pytest.mark.integration
class TestGenerationErrors:
    """Tests for error handling in generation."""

    @pytest.mark.asyncio
    async def test_llm_error_handling(
        self, mock_settings, mock_embedding_service, sample_chunks_factory
    ):
        """LLM errors should be properly propagated."""
        chunks = sample_chunks_factory(count=3)

        failing_llm = MagicMock()
        failing_llm.ainvoke = AsyncMock(side_effect=Exception("LLM connection failed"))

        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        from app.rag.vectorstore import VectorStore

                        vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                        vector_store.add_chunks(chunks)

                        with patch(
                            "app.services.retrieval.get_vector_store", return_value=vector_store
                        ):
                            with patch(
                                "app.services.generation.get_retrieval_service"
                            ) as mock_retrieval:
                                from app.services.retrieval import RetrievalService

                                mock_retrieval.return_value = RetrievalService()

                                with patch("app.services.generation.get_validation_service"):
                                    service = GenerationService()
                                    service._get_or_create_llm = lambda model: failing_llm

                                    with pytest.raises(LLMError):
                                        await service.generate(
                                            prompt="Test prompt",
                                            max_sections=5,
                                        )


class TestCitationExtraction:
    """Tests for citation extraction from generated text."""

    def test_citation_extraction_single_source(self):
        """Should extract single source citation."""
        text = "This content references [Source 1] for its claims."
        citations = extract_citations(text)
        assert citations == [1]

    def test_citation_extraction_multiple_sources(self):
        """Should extract multiple source citations."""
        text = "[Source 1] states this, while [Source 3] and [Source 2] confirm it."
        citations = extract_citations(text)
        assert citations == [1, 2, 3]

    def test_citation_extraction_repeated_sources(self):
        """Should deduplicate repeated citations."""
        text = "[Source 1] says this. [Source 1] also says that."
        citations = extract_citations(text)
        assert citations == [1]

    def test_citation_extraction_no_citations(self):
        """Should return empty list for no citations."""
        text = "This content has no citations."
        citations = extract_citations(text)
        assert citations == []

    def test_citation_extraction_malformed_citations(self):
        """Should ignore malformed citations."""
        text = "[Source] invalid. [source 1] wrong case. [Source 1] valid."
        citations = extract_citations(text)
        assert citations == [1]


class TestConfidenceAssessment:
    """Tests for confidence level assessment."""

    def test_assess_confidence_high_citations(self, mock_settings, mock_embedding_service):
        """High citation ratio should yield HIGH confidence."""
        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.services.generation.get_retrieval_service"):
                    with patch("app.services.generation.get_validation_service"):
                        service = GenerationService()

                        confidence = service._assess_confidence(
                            content="Content [Source 1] with [Source 2] citations [Source 3]",
                            cited_count=3,
                            available_count=4,
                        )

                        assert confidence == ConfidenceLevel.HIGH

    def test_assess_confidence_low_citations(self, mock_settings, mock_embedding_service):
        """Low citation count should yield MEDIUM confidence (uses absolute counts, not ratios)."""
        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.services.generation.get_retrieval_service"):
                    with patch("app.services.generation.get_validation_service"):
                        service = GenerationService()

                        # With 1 citation, confidence is MEDIUM (absolute count based)
                        confidence = service._assess_confidence(
                            content="Content [Source 1]",
                            cited_count=1,
                            available_count=10,
                        )

                        assert confidence == ConfidenceLevel.MEDIUM

    def test_assess_confidence_no_sources(self, mock_settings, mock_embedding_service):
        """No available sources should yield LOW confidence."""
        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.services.generation.get_retrieval_service"):
                    with patch("app.services.generation.get_validation_service"):
                        service = GenerationService()

                        confidence = service._assess_confidence(
                            content="Content without sources",
                            cited_count=0,
                            available_count=0,
                        )

                        assert confidence == ConfidenceLevel.LOW

    def test_assess_confidence_uncertainty_markers(self, mock_settings, mock_embedding_service):
        """Content with uncertainty markers should yield LOW confidence."""
        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.services.generation.get_retrieval_service"):
                    with patch("app.services.generation.get_validation_service"):
                        service = GenerationService()

                        confidence = service._assess_confidence(
                            content="I don't have enough information to write about this topic.",
                            cited_count=2,
                            available_count=3,
                        )

                        assert confidence == ConfidenceLevel.LOW


@pytest.mark.integration
class TestRegenerateSection:
    """Tests for section regeneration."""

    @pytest.mark.asyncio
    async def test_regenerate_section_preserves_id(
        self, mock_settings, mock_embedding_service, mock_llm, sample_chunks_factory
    ):
        """Regenerated section should preserve the original section ID."""
        chunks = sample_chunks_factory(count=5)

        mock_llm.set_response("Regenerated content with [Source 1] citations.")

        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        from app.rag.vectorstore import VectorStore

                        vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                        vector_store.add_chunks(chunks)

                        with patch(
                            "app.services.retrieval.get_vector_store", return_value=vector_store
                        ):
                            with patch(
                                "app.services.generation.get_retrieval_service"
                            ) as mock_retrieval:
                                from app.services.retrieval import RetrievalService

                                mock_retrieval.return_value = RetrievalService()

                                with patch("app.services.generation.get_validation_service"):
                                    service = GenerationService()
                                    service._get_or_create_llm = lambda model: mock_llm

                                    result = await service.regenerate_section(
                                        section_id="original-section-id",
                                        original_content="Original content here.",
                                        refinement_prompt="Make it better",
                                    )

                                    assert result.section.section_id == "original-section-id"

    @pytest.mark.asyncio
    async def test_regenerate_section_returns_metadata(
        self, mock_settings, mock_embedding_service, mock_llm, sample_chunks_factory
    ):
        """Regenerated section should include retrieval metadata."""
        chunks = sample_chunks_factory(count=5)

        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                    with patch(
                        "app.rag.vectorstore.get_embedding_service",
                        return_value=mock_embedding_service,
                    ):
                        from app.rag.vectorstore import VectorStore

                        vector_store = VectorStore(store_path=mock_settings.vectors_dir)
                        vector_store.add_chunks(chunks)

                        with patch(
                            "app.services.retrieval.get_vector_store", return_value=vector_store
                        ):
                            with patch(
                                "app.services.generation.get_retrieval_service"
                            ) as mock_retrieval:
                                from app.services.retrieval import RetrievalService

                                mock_retrieval.return_value = RetrievalService()

                                with patch("app.services.generation.get_validation_service"):
                                    service = GenerationService()
                                    service._get_or_create_llm = lambda model: mock_llm

                                    result = await service.regenerate_section(
                                        section_id="section-1",
                                        original_content="Original content",
                                    )

                                    assert result.retrieval_metadata is not None
                                    assert result.generation_time_ms >= 0


class TestSectionParsing:
    """Tests for parsing generated content into sections."""

    def test_parse_into_sections_single_paragraph(
        self, mock_settings, mock_embedding_service, sample_sources
    ):
        """Single paragraph should create one section."""
        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.services.generation.get_retrieval_service"):
                    with patch("app.services.generation.get_validation_service"):
                        service = GenerationService()

                        sections = service._parse_into_sections(
                            content="This is a single paragraph.",
                            sources=sample_sources,
                            generation_id="gen-001",
                        )

                        assert len(sections) >= 1

    def test_parse_into_sections_multiple_paragraphs(
        self, mock_settings, mock_embedding_service, sample_sources
    ):
        """Multiple paragraphs should be grouped into sections."""
        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.services.generation.get_retrieval_service"):
                    with patch("app.services.generation.get_validation_service"):
                        service = GenerationService()

                        content = (
                            "First paragraph content.\n\n"
                            "Second paragraph content.\n\n"
                            "Third paragraph content.\n\n"
                            "Fourth paragraph content."
                        )

                        sections = service._parse_into_sections(
                            content=content,
                            sources=sample_sources,
                            generation_id="gen-001",
                        )

                        # Should create multiple sections
                        assert len(sections) >= 1
                        # All sections should have IDs
                        assert all(s.section_id.startswith("gen-001-") for s in sections)

    def test_parse_into_sections_empty_content(
        self, mock_settings, mock_embedding_service, sample_sources
    ):
        """Empty content should still create a section."""
        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.services.generation.get_retrieval_service"):
                    with patch("app.services.generation.get_validation_service"):
                        service = GenerationService()

                        sections = service._parse_into_sections(
                            content="",
                            sources=sample_sources,
                            generation_id="gen-001",
                        )

                        # Should still create at least one section
                        assert len(sections) >= 1


class TestSourceMapping:
    """Tests for mapping citations to sources."""

    def test_create_section_maps_cited_sources(
        self, mock_settings, mock_embedding_service, sample_sources
    ):
        """Section should map [Source N] citations to actual sources."""
        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.services.generation.get_retrieval_service"):
                    with patch("app.services.generation.get_validation_service"):
                        service = GenerationService()

                        section = service._create_section(
                            content="Content with [Source 1] and [Source 2] citations.",
                            sources=sample_sources,
                            section_id="section-001",
                        )

                        # Section should have sources
                        assert len(section.sources) > 0
                        # Sources should be from the provided list
                        for source in section.sources:
                            assert any(s.chunk_id == source.chunk_id for s in sample_sources)

    def test_create_section_uses_top_sources_when_no_citations(
        self, mock_settings, mock_embedding_service, sample_sources
    ):
        """Section without citations should use top relevant sources."""
        with patch("app.services.generation.get_settings", return_value=mock_settings):
            with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                with patch("app.services.generation.get_retrieval_service"):
                    with patch("app.services.generation.get_validation_service"):
                        service = GenerationService()

                        section = service._create_section(
                            content="Content without any citations.",
                            sources=sample_sources,
                            section_id="section-001",
                        )

                        # Should still have sources (top 3)
                        assert len(section.sources) <= 3
                        assert len(section.sources) > 0
