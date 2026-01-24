"""Chat endpoints for multi-turn conversations with documents."""

from fastapi import APIRouter, HTTPException

from ...core import GenerationError, LLMError
from pydantic import BaseModel, Field

from ...models import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    ConversationSummaryResponse,
)
from ...services import get_chat_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a chat message and receive a response.

    Multi-turn conversation with documents:
    1. If conversation_id is None, starts a new conversation
    2. Otherwise, continues the existing conversation
    3. The LLM receives conversation history for context
    4. Sources are retrieved fresh for each message
    5. Cumulative coverage tracks what's been seen across turns

    Args:
        request: Chat request with message and optional conversation_id

    Returns:
        Chat response with the assistant's message and metadata
    """
    service = get_chat_service()

    try:
        result = await service.chat(
            conversation_id=request.conversation_id,
            message=request.message,
            document_ids=request.document_ids,
            include_history=request.include_history,
            history_turns=request.history_turns,
        )

        return result.to_response()

    except LLMError as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM service error: {e.message}. Ensure Ollama is running.",
        )
    except GenerationError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str) -> ConversationResponse:
    """Get a conversation by ID.

    Returns the full conversation history including all messages,
    sources used, and cumulative coverage.

    Args:
        conversation_id: The conversation ID

    Returns:
        The conversation with all messages
    """
    service = get_chat_service()

    conversation = service.get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation not found: {conversation_id}",
        )

    return ConversationResponse.from_dataclass(conversation)


@router.get("", response_model=list[ConversationSummaryResponse])
async def list_conversations() -> list[ConversationSummaryResponse]:
    """List all conversations.

    Returns conversations sorted by updated_at (newest first).
    Each entry includes a title (first user message, truncated) and metadata.

    Returns:
        List of conversation summaries
    """
    service = get_chat_service()
    summaries = service.list_conversations()
    return [ConversationSummaryResponse.from_dataclass(s) for s in summaries]


class UpdateTitleRequest(BaseModel):
    """Request to update a conversation's title."""
    title: str = Field(..., min_length=1, max_length=200)


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: UpdateTitleRequest,
) -> dict:
    """Update a conversation's title.

    Args:
        conversation_id: The conversation ID
        request: Request containing the new title

    Returns:
        Success message
    """
    service = get_chat_service()

    if not service.update_conversation_title(conversation_id, request.title):
        raise HTTPException(
            status_code=404,
            detail=f"Conversation not found: {conversation_id}",
        )

    return {"message": "Title updated successfully"}


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict:
    """Delete a conversation.

    Permanently removes the conversation and all its messages.

    Args:
        conversation_id: The conversation ID to delete

    Returns:
        Success message
    """
    service = get_chat_service()

    if not service.delete_conversation(conversation_id):
        raise HTTPException(
            status_code=404,
            detail=f"Conversation not found: {conversation_id}",
        )

    return {"message": "Conversation deleted successfully"}
