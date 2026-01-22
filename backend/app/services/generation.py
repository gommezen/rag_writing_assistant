"""Generation service for creating document drafts.

Uses retrieved context to generate grounded content with source citations.
"""

import time
from datetime import datetime
from uuid import uuid4

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_settings
from ..core import GenerationError, LLMError, get_logger
from ..models import (
    ConfidenceLevel,
    GeneratedSection,
    GenerationResult,
    RegenerationResult,
    SourceReference,
)
from ..rag import build_generation_prompt, build_regeneration_prompt, extract_citations
from .retrieval import get_retrieval_service
from .validation import get_validation_service

logger = get_logger(__name__)


class GenerationService:
    """Service for generating document content using RAG."""

    def __init__(self):
        """Initialize generation service."""
        self.settings = get_settings()
        self.retrieval_service = get_retrieval_service()
        self.validation_service = get_validation_service()
        self._llm: ChatOllama | None = None

    @property
    def llm(self) -> ChatOllama:
        """Lazy-load LLM client."""
        if self._llm is None:
            self._llm = ChatOllama(
                model=self.settings.generation_model,
                base_url=self.settings.ollama_base_url,
                temperature=0.7,
            )
        return self._llm

    async def generate(
        self,
        prompt: str,
        document_ids: list[str] | None = None,
        max_sections: int = 5,
    ) -> GenerationResult:
        """Generate a document draft based on prompt and retrieved context.

        Args:
            prompt: The writing prompt/topic
            document_ids: Optional list of document IDs to use
            max_sections: Maximum number of sections to generate

        Returns:
            GenerationResult with sections, sources, and metadata
        """
        start_time = time.time()
        generation_id = str(uuid4())

        logger.audit(
            action="generation_started",
            resource_type="generation",
            resource_id=generation_id,
            prompt_length=len(prompt),
            document_filter=document_ids,
        )

        # Retrieve relevant context
        sources, retrieval_metadata = self.retrieval_service.retrieve(
            query=prompt,
            document_ids=document_ids,
        )

        # Check if we have enough context
        warnings = self.validation_service.check_retrieval_quality(sources)

        # Build prompt with context
        source_dicts = [
            {
                "content": self._get_source_content(source),
                "metadata": source.metadata,
            }
            for source in sources
        ]

        system_prompt, user_prompt = build_generation_prompt(
            topic=prompt,
            sources=source_dicts,
        )

        # Generate content
        try:
            response = await self._generate_with_llm(system_prompt, user_prompt)
        except Exception as e:
            logger.error(
                "LLM generation failed",
                generation_id=generation_id,
                error=str(e),
            )
            raise LLMError(str(e), self.settings.generation_model)

        # Parse response into sections
        sections = self._parse_into_sections(
            content=response,
            sources=sources,
            generation_id=generation_id,
        )

        # Validate generated content
        for section in sections:
            section_warnings = self.validation_service.validate_section(
                section=section,
                available_sources=sources,
            )
            section.warnings.extend(section_warnings)

        generation_time_ms = (time.time() - start_time) * 1000

        result = GenerationResult(
            generation_id=generation_id,
            sections=sections,
            retrieval_metadata=retrieval_metadata,
            total_sources_used=len(set(s.document_id for s in sources)),
            generation_time_ms=generation_time_ms,
            model_used=self.settings.generation_model,
            created_at=datetime.utcnow(),
        )

        logger.audit(
            action="generation_completed",
            resource_type="generation",
            resource_id=generation_id,
            sections_count=len(sections),
            sources_used=result.total_sources_used,
            generation_time_ms=generation_time_ms,
        )

        return result

    async def regenerate_section(
        self,
        section_id: str,
        original_content: str,
        refinement_prompt: str | None = None,
        document_ids: list[str] | None = None,
    ) -> RegenerationResult:
        """Regenerate a specific section with optional refinement.

        Args:
            section_id: ID of section to regenerate
            original_content: Original section content
            refinement_prompt: Optional prompt for refinement
            document_ids: Optional document filter

        Returns:
            RegenerationResult with new section and metadata
        """
        start_time = time.time()

        logger.audit(
            action="regeneration_started",
            resource_type="section",
            resource_id=section_id,
            has_refinement=refinement_prompt is not None,
        )

        # Retrieve context
        query = refinement_prompt or original_content[:500]
        sources, retrieval_metadata = self.retrieval_service.retrieve(
            query=query,
            document_ids=document_ids,
        )

        # Build regeneration prompt
        source_dicts = [
            {
                "content": self._get_source_content(source),
                "metadata": source.metadata,
            }
            for source in sources
        ]

        system_prompt, user_prompt = build_regeneration_prompt(
            original_section=original_content,
            sources=source_dicts,
            refinement_instructions=refinement_prompt,
        )

        # Generate new content
        try:
            response = await self._generate_with_llm(system_prompt, user_prompt)
        except Exception as e:
            raise LLMError(str(e), self.settings.generation_model)

        # Create new section
        section = self._create_section(
            content=response,
            sources=sources,
            section_id=section_id,
        )

        # Validate
        section_warnings = self.validation_service.validate_section(
            section=section,
            available_sources=sources,
        )
        section.warnings.extend(section_warnings)

        generation_time_ms = (time.time() - start_time) * 1000

        result = RegenerationResult(
            section=section,
            retrieval_metadata=retrieval_metadata,
            generation_time_ms=generation_time_ms,
        )

        logger.audit(
            action="regeneration_completed",
            resource_type="section",
            resource_id=section_id,
            generation_time_ms=generation_time_ms,
        )

        return result

    async def _generate_with_llm(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate content using the LLM.

        Args:
            system_prompt: System message
            user_prompt: User message

        Returns:
            Generated text
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        return response.content

    def _parse_into_sections(
        self,
        content: str,
        sources: list[SourceReference],
        generation_id: str,
    ) -> list[GeneratedSection]:
        """Parse generated content into sections.

        Simple implementation: split by double newlines for paragraphs,
        group into logical sections.
        """
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        if not paragraphs:
            return [
                self._create_section(
                    content=content,
                    sources=sources,
                    section_id=f"{generation_id}-0",
                )
            ]

        # For MVP, create one section per significant paragraph group
        sections = []
        current_content = []
        section_idx = 0

        for para in paragraphs:
            current_content.append(para)

            # Create a new section every 2-3 paragraphs or on clear breaks
            if len(current_content) >= 2 or para.endswith(":"):
                section_text = "\n\n".join(current_content)
                section = self._create_section(
                    content=section_text,
                    sources=sources,
                    section_id=f"{generation_id}-{section_idx}",
                )
                sections.append(section)
                current_content = []
                section_idx += 1

        # Don't forget remaining content
        if current_content:
            section_text = "\n\n".join(current_content)
            section = self._create_section(
                content=section_text,
                sources=sources,
                section_id=f"{generation_id}-{section_idx}",
            )
            sections.append(section)

        return sections

    def _create_section(
        self,
        content: str,
        sources: list[SourceReference],
        section_id: str,
    ) -> GeneratedSection:
        """Create a GeneratedSection with appropriate metadata."""
        # Extract which sources were cited
        cited_indices = extract_citations(content)

        # Map cited sources
        section_sources = []
        for idx in cited_indices:
            if 1 <= idx <= len(sources):
                section_sources.append(sources[idx - 1])

        # If no citations found, include all sources but flag it
        if not section_sources:
            section_sources = sources[:3]  # Top 3 most relevant

        # Determine confidence based on citation quality
        confidence = self._assess_confidence(
            content=content,
            cited_count=len(cited_indices),
            available_count=len(sources),
        )

        return GeneratedSection(
            section_id=section_id,
            content=content,
            sources=section_sources,
            confidence=confidence,
            warnings=[],
            is_user_edited=False,
        )

    def _assess_confidence(
        self,
        content: str,
        cited_count: int,
        available_count: int,
    ) -> ConfidenceLevel:
        """Assess confidence level based on citation coverage."""
        if available_count == 0:
            return ConfidenceLevel.LOW

        # Check for explicit uncertainty markers
        uncertainty_markers = [
            "i don't have enough information",
            "insufficient context",
            "cannot find support",
            "no relevant sources",
        ]

        content_lower = content.lower()
        for marker in uncertainty_markers:
            if marker in content_lower:
                return ConfidenceLevel.LOW

        # Assess based on citation ratio
        if cited_count == 0:
            return ConfidenceLevel.UNKNOWN

        citation_ratio = cited_count / max(available_count, 1)

        if citation_ratio >= 0.5:
            return ConfidenceLevel.HIGH
        elif citation_ratio >= 0.2:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _get_source_content(self, source: SourceReference) -> str:
        """Get full content for a source reference."""
        # Access the vector store to get full chunk content
        vector_store = self.retrieval_service.vector_store
        for chunk in vector_store.chunks:
            if chunk.chunk_id == source.chunk_id:
                return chunk.content
        return source.excerpt


# Singleton instance
_generation_service: GenerationService | None = None


def get_generation_service() -> GenerationService:
    """Get the singleton generation service instance."""
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service
