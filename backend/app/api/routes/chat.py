"""Chat endpoints for multi-turn conversations with documents."""

from fastapi import APIRouter, HTTPException

from ...core import GenerationError, LLMError
from ...models import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
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
