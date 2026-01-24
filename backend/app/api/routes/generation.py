"""Generation endpoints for creating document drafts."""

from fastapi import APIRouter, HTTPException

from ...core import GenerationError, LLMError
from ...models import (
    GenerationRequest,
    GenerationResponse,
    RegenerateSectionRequest,
    RegenerateSectionResponse,
    SuggestedQuestionsRequest,
    SuggestedQuestionsResponse,
)
from ...services import get_generation_service

router = APIRouter(prefix="/generate", tags=["Generation"])


@router.post("", response_model=GenerationResponse)
async def generate_draft(request: GenerationRequest) -> GenerationResponse:
    """Generate a document draft based on the provided prompt.

    The draft is generated using RAG (Retrieval-Augmented Generation):
    1. Intent is detected to determine retrieval strategy
    2. Relevant chunks are retrieved (similarity or diverse sampling)
    3. Coverage is computed before prompting
    4. The LLM generates content grounded in the retrieved context
    5. Each section includes source references and confidence levels

    Intent modes:
    - ANALYSIS: Uses diverse sampling for representative coverage
    - QA: Uses similarity search with higher top_k for Q&A
    - WRITING: Uses standard similarity search for content creation

    Args:
        request: Generation request with prompt and optional overrides

    Returns:
        Generated sections with sources, confidence, coverage, and warnings
    """
    service = get_generation_service()

    try:
        result = await service.generate(
            prompt=request.prompt,
            document_ids=request.document_ids,
            max_sections=request.max_sections,
            intent_override=request.intent_override,
            retrieval_type_override=request.retrieval_type_override,
            escalate_coverage=request.escalate_coverage,
        )

        return result.to_response()

    except LLMError as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM service error: {e.message}. Ensure Ollama is running.",
        )
    except GenerationError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/section", response_model=RegenerateSectionResponse)
async def regenerate_section(request: RegenerateSectionRequest) -> RegenerateSectionResponse:
    """Regenerate a specific section with optional refinement.

    Use this endpoint to:
    - Regenerate a section that needs improvement
    - Refine a section with additional instructions
    - Generate a section using different source documents

    Args:
        request: Regeneration request with section ID and optional refinement

    Returns:
        Regenerated section with updated sources and metadata
    """
    service = get_generation_service()

    try:
        result = await service.regenerate_section(
            section_id=request.section_id,
            original_content=request.original_content,
            refinement_prompt=request.refinement_prompt,
            document_ids=request.document_ids,
        )

        return result.to_response()

    except LLMError as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM service error: {e.message}. Ensure Ollama is running.",
        )
    except GenerationError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/suggestions", response_model=SuggestedQuestionsResponse)
async def generate_suggestions(
    request: SuggestedQuestionsRequest,
) -> SuggestedQuestionsResponse:
    """Generate suggested questions based on uploaded documents.

    This endpoint analyzes the content of uploaded documents and generates
    thoughtful questions that users might want to explore or write about.

    Args:
        request: Request with optional document filter and number of questions

    Returns:
        List of suggested questions with metadata
    """
    service = get_generation_service()

    try:
        result = await service.generate_suggestions(
            document_ids=request.document_ids,
            num_questions=request.num_questions,
        )

        return result

    except LLMError as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM service error: {e.message}. Ensure Ollama is running.",
        )
    except GenerationError as e:
        raise HTTPException(status_code=500, detail=e.message)
