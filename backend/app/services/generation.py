"""Generation service for creating document drafts.

Uses retrieved context to generate grounded content with source citations.
"""

import time
from datetime import UTC, datetime
from uuid import uuid4

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_settings
from ..core import GenerationError, LLMError, get_logger
from ..models import (
    ConfidenceLevel,
    CoverageDescriptor,
    GeneratedSection,
    GenerationResult,
    IntentClassification,
    QueryIntent,
    RegenerationResult,
    RetrievalType,
    SourceReference,
    SuggestedQuestionsResponse,
    SummaryScope,
)
from ..rag import (
    build_analysis_prompt,
    build_coverage_aware_generation_prompt,
    build_exploratory_summary_prompt,
    build_focused_summary_prompt,
    build_generation_prompt,
    build_regeneration_prompt,
    build_suggested_questions_prompt,
    extract_citations,
    parse_questions,
    sanitize_citations,
)
from .diverse_retrieval import get_diverse_retrieval_service
from .intent import get_intent_service
from .retrieval import get_retrieval_service
from .validation import get_validation_service

logger = get_logger(__name__)


class GenerationService:
    """Service for generating document content using RAG."""

    def __init__(self):
        """Initialize generation service."""
        self.settings = get_settings()
        self.retrieval_service = get_retrieval_service()
        self.diverse_retrieval_service = get_diverse_retrieval_service()
        self.intent_service = get_intent_service()
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
        intent_override: str | None = None,
        retrieval_type_override: str | None = None,
        escalate_coverage: bool = False,
    ) -> GenerationResult:
        """Generate a document draft based on prompt and retrieved context.

        Uses intent detection to determine retrieval strategy:
        - ANALYSIS: Diverse sampling for representative coverage
        - QA/WRITING: Similarity search for relevant context

        Args:
            prompt: The writing prompt/topic
            document_ids: Optional list of document IDs to use
            max_sections: Maximum number of sections to generate
            intent_override: Override detected intent ('analysis', 'qa', 'writing')
            retrieval_type_override: Override retrieval strategy ('similarity', 'diverse')
            escalate_coverage: Increase chunk sampling for more coverage

        Returns:
            GenerationResult with sections, sources, and metadata
        """
        start_time = time.time()
        generation_id = str(uuid4())

        # Step 1: Detect intent (or use override)
        if intent_override:
            intent = self._parse_intent_override(intent_override)
        else:
            intent = self.intent_service.detect_intent(prompt)

        # Step 2: Determine retrieval type
        if retrieval_type_override:
            retrieval_type = self._parse_retrieval_override(retrieval_type_override)
        else:
            retrieval_type = intent.suggested_retrieval

        logger.audit(
            action="generation_started",
            resource_type="generation",
            resource_id=generation_id,
            prompt_length=len(prompt),
            document_filter=document_ids,
            detected_intent=intent.intent.value,
            retrieval_type=retrieval_type.value,
            summary_scope=intent.summary_scope.value,
            focus_topic=intent.focus_topic,
        )

        # Step 3: Retrieve context based on strategy
        if retrieval_type == RetrievalType.DIVERSE:
            sources, retrieval_metadata, coverage = self.diverse_retrieval_service.retrieve_diverse(
                document_ids=document_ids,
                target_chunks=30,
                escalate=escalate_coverage,
            )
            retrieval_metadata.intent = intent
        else:
            # Similarity-based retrieval (existing behavior)
            top_k = 20 if intent.intent == QueryIntent.QA else None  # Higher top_k for QA
            sources, retrieval_metadata = self.retrieval_service.retrieve(
                query=prompt,
                document_ids=document_ids,
                top_k=top_k,
            )
            # Compute coverage AFTER retrieval
            coverage = self.retrieval_service.compute_similarity_coverage(
                sources=sources,
                document_ids=document_ids,
            )
            retrieval_metadata.retrieval_type = retrieval_type
            retrieval_metadata.coverage = coverage
            retrieval_metadata.intent = intent

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

        # Step 4: Choose prompt based on intent and summary scope
        if intent.intent == QueryIntent.ANALYSIS:
            # For ANALYSIS intent, use summary scope to select prompt
            if intent.summary_scope == SummaryScope.FOCUSED and intent.focus_topic:
                # Focused summary: deep synthesis on specific topic
                system_prompt, user_prompt = build_focused_summary_prompt(
                    focus_topic=intent.focus_topic,
                    sources=source_dicts,
                    coverage_summary=coverage.coverage_summary,
                )
            else:
                # Broad summary: exploratory overview with suggested focus areas
                system_prompt, user_prompt = build_exploratory_summary_prompt(
                    sources=source_dicts,
                    coverage_summary=coverage.coverage_summary,
                )
        else:
            # For QA and WRITING, use coverage-aware generation prompt
            system_prompt, user_prompt = build_coverage_aware_generation_prompt(
                topic=prompt,
                sources=source_dicts,
                coverage_summary=coverage.coverage_summary,
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

        # Sanitize citations - remove any that reference non-existent sources
        response = sanitize_citations(response, len(sources))

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

            # Add epistemic warnings for analysis mode with low coverage
            if intent.intent == QueryIntent.ANALYSIS and coverage.coverage_percentage < 20:
                section.warnings.append(
                    f"Analysis based on ~{coverage.coverage_percentage:.0f}% document coverage - "
                    "treat conclusions as exploratory"
                )

        generation_time_ms = (time.time() - start_time) * 1000

        result = GenerationResult(
            generation_id=generation_id,
            sections=sections,
            retrieval_metadata=retrieval_metadata,
            total_sources_used=len(set(s.document_id for s in sources)),
            generation_time_ms=generation_time_ms,
            model_used=self.settings.generation_model,
            created_at=datetime.now(UTC),
        )

        logger.audit(
            action="generation_completed",
            resource_type="generation",
            resource_id=generation_id,
            sections_count=len(sections),
            sources_used=result.total_sources_used,
            generation_time_ms=generation_time_ms,
            intent=intent.intent.value,
            coverage_percentage=round(coverage.coverage_percentage, 1),
        )

        return result

    def _parse_intent_override(self, override: str) -> IntentClassification:
        """Parse intent override string into IntentClassification."""
        intent_map = {
            "analysis": QueryIntent.ANALYSIS,
            "qa": QueryIntent.QA,
            "writing": QueryIntent.WRITING,
        }
        intent = intent_map.get(override.lower(), QueryIntent.WRITING)

        retrieval_map = {
            QueryIntent.ANALYSIS: RetrievalType.DIVERSE,
            QueryIntent.QA: RetrievalType.SIMILARITY,
            QueryIntent.WRITING: RetrievalType.SIMILARITY,
        }

        return IntentClassification(
            intent=intent,
            confidence=1.0,
            reasoning=f"User override: {override}",
            suggested_retrieval=retrieval_map[intent],
        )

    def _parse_retrieval_override(self, override: str) -> RetrievalType:
        """Parse retrieval type override string."""
        if override.lower() == "diverse":
            return RetrievalType.DIVERSE
        return RetrievalType.SIMILARITY

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

        # Sanitize citations - remove any that reference non-existent sources
        response = sanitize_citations(response, len(sources))

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

    async def generate_suggestions(
        self,
        document_ids: list[str] | None = None,
        num_questions: int = 5,
    ) -> SuggestedQuestionsResponse:
        """Generate suggested questions based on document content.

        Args:
            document_ids: Optional list of document IDs to use
            num_questions: Number of questions to generate

        Returns:
            SuggestedQuestionsResponse with generated questions
        """
        start_time = time.time()

        logger.audit(
            action="suggestions_started",
            resource_type="suggestions",
            document_filter=document_ids,
            num_questions=num_questions,
        )

        # Retrieve a sample of content from documents
        # Use a generic query to get diverse chunks
        sources, _ = self.retrieval_service.retrieve(
            query="main topics and key information",
            document_ids=document_ids,
            top_k=10,  # Get more chunks for better question diversity
        )

        if not sources:
            return SuggestedQuestionsResponse(
                questions=["What topics would you like to explore? Upload documents to get started."],
                source_documents=[],
                generation_time_ms=(time.time() - start_time) * 1000,
            )

        # Build prompt with context
        source_dicts = [
            {
                "content": self._get_source_content(source),
                "metadata": source.metadata,
            }
            for source in sources
        ]

        system_prompt, user_prompt = build_suggested_questions_prompt(
            sources=source_dicts,
            num_questions=num_questions,
        )

        # Generate questions
        try:
            response = await self._generate_with_llm(system_prompt, user_prompt)
        except Exception as e:
            logger.error(
                "Suggestions generation failed",
                error=str(e),
            )
            raise LLMError(str(e), self.settings.generation_model)

        # Parse questions from response
        questions = parse_questions(response)

        # If parsing failed, try to extract any lines that look like questions
        if not questions:
            questions = [
                line.strip()
                for line in response.strip().split("\n")
                if line.strip() and line.strip().endswith("?")
            ][:num_questions]

        # Get unique document IDs used
        source_document_ids = list(set(s.document_id for s in sources))

        generation_time_ms = (time.time() - start_time) * 1000

        logger.audit(
            action="suggestions_completed",
            resource_type="suggestions",
            questions_count=len(questions),
            generation_time_ms=generation_time_ms,
        )

        return SuggestedQuestionsResponse(
            questions=questions,
            source_documents=source_document_ids,
            generation_time_ms=generation_time_ms,
        )

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

        Split on markdown headings (## or ###) for structured documents.
        For unstructured content like cover letters, keep as single section.
        """
        import re

        # Check for markdown headings - if present, split on them
        heading_pattern = r'^#{2,3}\s+.+$'
        has_headings = bool(re.search(heading_pattern, content, re.MULTILINE))

        if has_headings:
            # Split on markdown headings, keeping the heading with its content
            parts = re.split(r'(^#{2,3}\s+.+$)', content, flags=re.MULTILINE)
            sections = []
            section_idx = 0
            current_content = []

            for part in parts:
                part = part.strip()
                if not part:
                    continue

                if re.match(heading_pattern, part):
                    # Save previous section if exists
                    if current_content:
                        section_text = "\n\n".join(current_content)
                        section = self._create_section(
                            content=section_text,
                            sources=sources,
                            section_id=f"{generation_id}-{section_idx}",
                        )
                        sections.append(section)
                        section_idx += 1
                        current_content = []
                    current_content.append(part)
                else:
                    current_content.append(part)

            # Don't forget remaining content
            if current_content:
                section_text = "\n\n".join(current_content)
                section = self._create_section(
                    content=section_text,
                    sources=sources,
                    section_id=f"{generation_id}-{section_idx}",
                )
                sections.append(section)

            return sections if sections else [self._create_section(
                content=content,
                sources=sources,
                section_id=f"{generation_id}-0",
            )]

        # No headings found - treat as single cohesive document (e.g., cover letter)
        # Split into sections only if content is very long (>1500 chars)
        if len(content) > 1500:
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            sections = []
            current_content = []
            section_idx = 0

            for para in paragraphs:
                current_content.append(para)
                # Create section every 3-4 paragraphs for long content
                if len(current_content) >= 4:
                    section_text = "\n\n".join(current_content)
                    section = self._create_section(
                        content=section_text,
                        sources=sources,
                        section_id=f"{generation_id}-{section_idx}",
                    )
                    sections.append(section)
                    current_content = []
                    section_idx += 1

            if current_content:
                section_text = "\n\n".join(current_content)
                section = self._create_section(
                    content=section_text,
                    sources=sources,
                    section_id=f"{generation_id}-{section_idx}",
                )
                sections.append(section)

            return sections

        # Short content without headings - keep as single section
        return [
            self._create_section(
                content=content,
                sources=sources,
                section_id=f"{generation_id}-0",
            )
        ]

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
        """Assess confidence level based on citation count per section."""
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

        # Assess based on absolute citation count (more practical for sections)
        if cited_count == 0:
            return ConfidenceLevel.UNKNOWN
        elif cited_count >= 3:
            return ConfidenceLevel.HIGH
        elif cited_count >= 1:
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
