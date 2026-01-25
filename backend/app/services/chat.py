"""Chat service for multi-turn conversations with documents.

Manages conversation state, history, and coordinates retrieval and generation
for conversational RAG interactions.
"""

import time
from datetime import UTC, datetime
from uuid import uuid4

from ..config import get_settings
from ..core import get_logger, RetrievalError
from ..models import (
    ChatMessage,
    ChatResult,
    ChatRole,
    ContextUsedResponse,
    Conversation,
    ConversationSummary,
    CoverageDescriptor,
    DocumentCoverage,
    GeneratedSection,
    QueryIntent,
    RetrievalMetadata,
    RetrievalType,
    SourceReference,
)
from ..rag import build_chat_prompt, sanitize_citations, extract_citations
from .conversation_store import ConversationStore
from .generation import get_generation_service
from .intent import get_intent_service
from .retrieval import get_retrieval_service

logger = get_logger(__name__)


class ChatService:
    """Service for managing multi-turn chat conversations."""

    def __init__(self):
        """Initialize chat service."""
        self.settings = get_settings()
        self.generation_service = get_generation_service()
        self.retrieval_service = get_retrieval_service()
        self.intent_service = get_intent_service()
        # Persistent conversation storage
        self.store = ConversationStore(self.settings.conversations_dir)
        # In-memory cache for active conversations
        self.conversations: dict[str, Conversation] = {}
        # Load existing conversations from store
        self._load_from_store()

    def _load_from_store(self) -> None:
        """Load all conversations from persistent storage into memory cache."""
        for summary in self.store.list_conversations():
            conversation = self.store.load_conversation(summary.conversation_id)
            if conversation:
                self.conversations[conversation.conversation_id] = conversation
        logger.info(
            "Loaded conversations from store",
            conversation_count=len(self.conversations),
        )

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID.

        Args:
            conversation_id: The conversation ID

        Returns:
            The conversation or None if not found
        """
        return self.conversations.get(conversation_id)

    def _get_or_create_conversation(
        self,
        conversation_id: str | None,
        document_ids: list[str] | None,
    ) -> Conversation:
        """Get an existing conversation or create a new one.

        Args:
            conversation_id: Existing conversation ID, or None to create new
            document_ids: Document IDs to scope the conversation

        Returns:
            The conversation (existing or new)
        """
        if conversation_id and conversation_id in self.conversations:
            conversation = self.conversations[conversation_id]
            conversation.updated_at = datetime.now(UTC)
            return conversation

        # Create new conversation
        new_id = str(uuid4())
        conversation = Conversation(
            conversation_id=new_id,
            messages=[],
            document_ids=document_ids,
            cumulative_coverage=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.conversations[new_id] = conversation
        # Persist new conversation immediately
        self.store.save_conversation(conversation)

        logger.info(
            "Created new conversation",
            conversation_id=new_id,
            document_ids=document_ids,
        )

        return conversation

    def _create_user_message(self, content: str) -> ChatMessage:
        """Create a user message.

        Args:
            content: The message content

        Returns:
            A new ChatMessage with user role
        """
        return ChatMessage(
            message_id=str(uuid4()),
            role=ChatRole.USER,
            content=content,
            timestamp=datetime.now(UTC),
            sections=None,
            sources_used=[],
        )

    def _create_assistant_message(
        self,
        content: str,
        sources: list[SourceReference],
        sections: list[GeneratedSection] | None = None,
    ) -> ChatMessage:
        """Create an assistant message.

        Args:
            content: The response content
            sources: Sources used for this response
            sections: Optional parsed sections

        Returns:
            A new ChatMessage with assistant role
        """
        return ChatMessage(
            message_id=str(uuid4()),
            role=ChatRole.ASSISTANT,
            content=content,
            timestamp=datetime.now(UTC),
            sections=sections,
            sources_used=sources,
        )

    def _get_conversation_history(
        self,
        conversation: Conversation,
        max_turns: int = 5,
    ) -> tuple[list[tuple[str, str]], bool]:
        """Get recent conversation history as (role, content) tuples.

        Args:
            conversation: The conversation
            max_turns: Maximum number of prior turns to include

        Returns:
            Tuple of (history list, was_truncated)
        """
        history: list[tuple[str, str]] = []
        messages = conversation.messages

        # Take last N*2 messages (N turns = N user + N assistant messages)
        max_messages = max_turns * 2
        truncated = len(messages) > max_messages

        recent_messages = messages[-max_messages:] if truncated else messages

        for msg in recent_messages:
            history.append((msg.role.value, msg.content))

        return history, truncated

    def _update_cumulative_coverage(
        self,
        conversation: Conversation,
        new_sources: list[SourceReference],
        retrieval_metadata: RetrievalMetadata,
    ) -> None:
        """Update cumulative coverage tracking for the conversation.

        Args:
            conversation: The conversation to update
            new_sources: New sources retrieved this turn
            retrieval_metadata: Metadata from this retrieval
        """
        # Get existing cumulative coverage or initialize
        if conversation.cumulative_coverage is None:
            conversation.cumulative_coverage = CoverageDescriptor(
                retrieval_type=RetrievalType.SIMILARITY,
                chunks_seen=0,
                chunks_total=0,
                coverage_percentage=0.0,
                document_coverage={},
                blind_spots=[],
                coverage_summary="",
            )

        # Track unique chunks seen
        existing_chunk_ids = set()
        for msg in conversation.messages:
            for source in msg.sources_used:
                existing_chunk_ids.add(source.chunk_id)

        new_chunk_ids = {s.chunk_id for s in new_sources}
        all_chunk_ids = existing_chunk_ids | new_chunk_ids

        # Update coverage counts
        conversation.cumulative_coverage.chunks_seen = len(all_chunk_ids)

        # Use coverage from retrieval metadata if available
        # Track the MAX chunks_total seen (documents may change between turns)
        if retrieval_metadata.coverage:
            new_total = retrieval_metadata.coverage.chunks_total
            # Keep the larger total to account for document selection changes
            conversation.cumulative_coverage.chunks_total = max(
                conversation.cumulative_coverage.chunks_total,
                new_total
            )

        # Calculate percentage (cap at 100% in case of document selection changes)
        chunks_total = conversation.cumulative_coverage.chunks_total
        if chunks_total > 0:
            coverage_pct = min((len(all_chunk_ids) / chunks_total * 100), 100.0)
            conversation.cumulative_coverage.coverage_percentage = round(coverage_pct, 1)

            # Build coverage summary for prompt
            conversation.cumulative_coverage.coverage_summary = (
                f"Across this conversation, you have seen {len(all_chunk_ids)} of "
                f"{chunks_total} total chunks "
                f"(~{conversation.cumulative_coverage.coverage_percentage:.0f}% cumulative coverage)."
            )

    def _build_cumulative_coverage_info(self, conversation: Conversation) -> str:
        """Build human-readable cumulative coverage info for prompt.

        Args:
            conversation: The conversation

        Returns:
            Coverage summary string
        """
        if conversation.cumulative_coverage and conversation.cumulative_coverage.coverage_summary:
            return conversation.cumulative_coverage.coverage_summary

        # Count unique sources across conversation
        all_chunk_ids = set()
        for msg in conversation.messages:
            for source in msg.sources_used:
                all_chunk_ids.add(source.chunk_id)

        if not all_chunk_ids:
            return "This is the start of the conversation. No prior sources have been retrieved."

        return f"Across this conversation, you have seen {len(all_chunk_ids)} unique document chunks."

    async def chat(
        self,
        conversation_id: str | None,
        message: str,
        document_ids: list[str] | None = None,
        include_history: bool = True,
        history_turns: int = 5,
    ) -> ChatResult:
        """Process a chat message and generate a response.

        Args:
            conversation_id: Existing conversation ID, or None to start new
            message: The user's message
            document_ids: Document IDs to scope retrieval (only for new conversations)
            include_history: Whether to include conversation history in context
            history_turns: Number of prior turns to include

        Returns:
            ChatResult with the response and metadata
        """
        start_time = time.time()

        # Get or create conversation
        conversation = self._get_or_create_conversation(conversation_id, document_ids)

        # Use conversation's document_ids if not specified
        effective_doc_ids = document_ids or conversation.document_ids

        # Add user message to conversation
        user_message = self._create_user_message(message)
        conversation.messages.append(user_message)

        # Detect intent for this message
        intent = self.intent_service.detect_intent(message)

        logger.info(
            "Chat message intent detected",
            conversation_id=conversation.conversation_id,
            intent=intent.intent.value,
            confidence=intent.confidence,
        )

        # Retrieve sources for this turn
        # Always re-retrieve (follow-ups may shift topic)
        sources, retrieval_metadata = self.retrieval_service.retrieve(
            query=message,
            document_ids=effective_doc_ids,
            top_k=self.settings.top_k_retrieval,
        )

        # Compute coverage for this retrieval (needed for cumulative tracking)
        retrieval_metadata.coverage = self.retrieval_service.compute_similarity_coverage(
            sources=sources,
            document_ids=effective_doc_ids,
        )

        if not sources:
            logger.warning(
                "No sources retrieved for chat message",
                conversation_id=conversation.conversation_id,
                message_preview=message[:100],
            )

        # Update cumulative coverage
        self._update_cumulative_coverage(conversation, sources, retrieval_metadata)

        # Get conversation history
        history, was_truncated = self._get_conversation_history(
            conversation,
            max_turns=history_turns if include_history else 0,
        )

        # Remove the current user message from history (we add it separately in prompt)
        if history and history[-1][0] == "user":
            history = history[:-1]

        # Build cumulative coverage info
        cumulative_coverage_info = self._build_cumulative_coverage_info(conversation)

        # Build source dicts for prompt
        source_dicts = [
            {
                "content": self._get_source_content(source),
                "metadata": source.metadata,
            }
            for source in sources
        ]

        # Build chat prompt
        system_prompt, user_prompt = build_chat_prompt(
            user_message=message,
            sources=source_dicts,
            conversation_history=history,
            cumulative_coverage_info=cumulative_coverage_info,
        )

        # Generate response with history
        response_content, model_used = await self.generation_service._generate_with_history(
            system_prompt=system_prompt,
            conversation_history=history,
            user_prompt=user_prompt,
            intent=intent.intent,
        )

        # Sanitize citations
        response_content = sanitize_citations(response_content, len(sources))

        # Create assistant message
        assistant_message = self._create_assistant_message(
            content=response_content,
            sources=sources,
            sections=None,  # For chat mode, we don't parse into sections
        )
        conversation.messages.append(assistant_message)

        # Persist conversation after each turn
        self.store.save_conversation(conversation)

        generation_time_ms = (time.time() - start_time) * 1000

        # Build context used info for transparency
        context_used = ContextUsedResponse(
            history_messages_count=len(history),
            history_truncated=was_truncated,
            sources_count=len(sources),
        )

        logger.info(
            "Chat response generated",
            conversation_id=conversation.conversation_id,
            message_id=assistant_message.message_id,
            sources_count=len(sources),
            history_messages=len(history),
            generation_time_ms=generation_time_ms,
            model_used=model_used,
        )

        return ChatResult(
            conversation=conversation,
            message=assistant_message,
            context_used=context_used,
            generation_time_ms=generation_time_ms,
            model_used=model_used,
        )

    def _get_source_content(self, source: SourceReference) -> str:
        """Get full content for a source reference.

        Args:
            source: The source reference

        Returns:
            The source content
        """
        # Access the vector store to get full chunk content
        vector_store = self.retrieval_service.vector_store
        for chunk in vector_store.chunks:
            if chunk.chunk_id == source.chunk_id:
                return chunk.content
        # Fallback to excerpt if chunk not found
        return source.excerpt

    def list_conversations(self) -> list[ConversationSummary]:
        """List all conversations sorted by updated_at (newest first).

        Returns:
            List of conversation summaries
        """
        return self.store.list_conversations()

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation.

        Args:
            conversation_id: The conversation ID to delete

        Returns:
            True if deleted, False if not found
        """
        # Remove from memory cache
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]

        # Remove from persistent storage
        result = self.store.delete_conversation(conversation_id)

        if result:
            logger.info(
                "Deleted conversation",
                conversation_id=conversation_id,
            )

        return result

    def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update a conversation's title.

        Args:
            conversation_id: The conversation ID
            title: The new title

        Returns:
            True if updated, False if not found
        """
        return self.store.update_title(conversation_id, title)


# Singleton instance
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """Get the singleton chat service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
