"""Generation endpoints for creating document drafts."""

from fastapi import APIRouter, HTTPException

from ...core import GenerationError, LLMError
from ...models import (
    GenerationRequest,
    GenerationResponse,
    RegenerateSectionRequest,
    RegenerateSectionResponse,
)
from ...services import get_generation_service

router = APIRouter(prefix="/generate", tags=["Generation"])


@router.post("", response_model=GenerationResponse)
async def generate_draft(request: GenerationRequest) -> GenerationResponse:
    """Generate a document draft based on the provided prompt.

    The draft is generated using RAG (Retrieval-Augmented Generation):
    1. Relevant chunks are retrieved from uploaded documents
    2. The LLM generates content grounded in the retrieved context
    3. Each section includes source references and confidence levels

    Args:
        request: Generation request with prompt and optional document filter

    Returns:
        Generated sections with sources, confidence, and warnings
    """
    service = get_generation_service()

    try:
        result = await service.generate(
            prompt=request.prompt,
            document_ids=request.document_ids,
            max_sections=request.max_sections,
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
        # For regeneration, we need the original content
        # In a full implementation, we'd look this up from session state
        # For MVP, the client should send the original content
        original_content = request.prompt or "Previous content not available."

        result = await service.regenerate_section(
            section_id=request.section_id,
            original_content=original_content,
            refinement_prompt=request.prompt,
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
