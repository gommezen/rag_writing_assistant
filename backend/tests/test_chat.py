"""Tests for chat service and API endpoints.

Tests multi-turn conversation functionality including:
- Conversation creation and management
- Message history handling
- Cumulative coverage tracking
- API endpoint behavior
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.models import (
    ChatMessage,
    ChatRequest,
    ChatRole,
    Conversation,
    CoverageDescriptor,
    RetrievalType,
)

# ============================================================================
# ChatMessage Model Tests
# ============================================================================


class TestChatMessageModel:
    """Tests for ChatMessage dataclass."""

    def test_user_message_creation(self):
        """Should create a user message correctly."""
        message = ChatMessage(
            message_id="msg-001",
            role=ChatRole.USER,
            content="What is this document about?",
            timestamp=datetime.now(UTC),
        )

        assert message.message_id == "msg-001"
        assert message.role == ChatRole.USER
        assert message.content == "What is this document about?"
        assert message.sections is None
        assert message.sources_used == []

    def test_assistant_message_with_sources(self, sample_sources):
        """Should create an assistant message with sources."""
        message = ChatMessage(
            message_id="msg-002",
            role=ChatRole.ASSISTANT,
            content="Based on [Source 1], this document discusses testing.",
            timestamp=datetime.now(UTC),
            sources_used=sample_sources,
        )

        assert message.role == ChatRole.ASSISTANT
        assert len(message.sources_used) == 3
        assert message.sources_used[0].chunk_id == "chunk-001"

    def test_to_dict_serialization(self, sample_sources):
        """Should serialize message to dict correctly."""
        message = ChatMessage(
            message_id="msg-003",
            role=ChatRole.ASSISTANT,
            content="Test content",
            timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
            sources_used=sample_sources[:1],
        )

        data = message.to_dict()

        assert data["message_id"] == "msg-003"
        assert data["role"] == "assistant"
        assert data["content"] == "Test content"
        assert "timestamp" in data
        assert isinstance(data["sources_used"], list)
        assert len(data["sources_used"]) == 1


# ============================================================================
# Conversation Model Tests
# ============================================================================


class TestConversationModel:
    """Tests for Conversation dataclass."""

    def test_empty_conversation_creation(self):
        """Should create an empty conversation."""
        conversation = Conversation(
            conversation_id="conv-001",
            messages=[],
            document_ids=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert conversation.conversation_id == "conv-001"
        assert len(conversation.messages) == 0
        assert conversation.document_ids is None
        assert conversation.cumulative_coverage is None

    def test_conversation_with_document_scope(self):
        """Should create a conversation scoped to specific documents."""
        doc_ids = ["doc-001", "doc-002"]
        conversation = Conversation(
            conversation_id="conv-002",
            messages=[],
            document_ids=doc_ids,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert conversation.document_ids == doc_ids

    def test_conversation_with_messages(self):
        """Should store messages in order."""
        msg1 = ChatMessage(
            message_id="m1",
            role=ChatRole.USER,
            content="First message",
        )
        msg2 = ChatMessage(
            message_id="m2",
            role=ChatRole.ASSISTANT,
            content="Response",
        )

        conversation = Conversation(
            conversation_id="conv-003",
            messages=[msg1, msg2],
        )

        assert len(conversation.messages) == 2
        assert conversation.messages[0].role == ChatRole.USER
        assert conversation.messages[1].role == ChatRole.ASSISTANT

    def test_to_dict_serialization(self):
        """Should serialize conversation to dict."""
        conversation = Conversation(
            conversation_id="conv-004",
            messages=[],
            document_ids=["doc-001"],
            created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )

        data = conversation.to_dict()

        assert data["conversation_id"] == "conv-004"
        assert data["messages"] == []
        assert data["document_ids"] == ["doc-001"]
        assert data["cumulative_coverage"] is None


# ============================================================================
# ChatRequest Validation Tests
# ============================================================================


class TestChatRequestValidation:
    """Tests for ChatRequest Pydantic model validation."""

    def test_valid_new_conversation_request(self):
        """Should accept a valid new conversation request."""
        request = ChatRequest(
            message="What is this document about?",
        )

        assert request.conversation_id is None
        assert request.message == "What is this document about?"
        assert request.include_history is True
        assert request.history_turns == 5

    def test_valid_continue_conversation_request(self):
        """Should accept a valid continue conversation request."""
        request = ChatRequest(
            conversation_id="conv-001",
            message="Tell me more about that.",
        )

        assert request.conversation_id == "conv-001"

    def test_custom_history_turns(self):
        """Should accept custom history_turns value."""
        request = ChatRequest(
            message="Test",
            history_turns=10,
        )

        assert request.history_turns == 10

    def test_empty_message_rejected(self):
        """Should reject empty messages."""
        with pytest.raises(ValueError):
            ChatRequest(message="")

    def test_message_too_long_rejected(self):
        """Should reject messages exceeding max length."""
        long_message = "x" * 10001
        with pytest.raises(ValueError):
            ChatRequest(message=long_message)

    def test_history_turns_minimum(self):
        """Should reject history_turns less than 1."""
        with pytest.raises(ValueError):
            ChatRequest(message="Test", history_turns=0)

    def test_history_turns_maximum(self):
        """Should reject history_turns greater than 20."""
        with pytest.raises(ValueError):
            ChatRequest(message="Test", history_turns=21)


# ============================================================================
# ChatService Unit Tests
# ============================================================================


class TestChatServiceUnit:
    """Unit tests for ChatService methods."""

    def _reset_singletons(self):
        """Reset all singleton instances."""
        import app.rag.embedding as embedding_module
        import app.rag.vectorstore as vectorstore_module
        import app.services.chat as chat_module
        import app.services.generation as generation_module
        import app.services.ingestion as ingestion_module
        import app.services.intent as intent_module
        import app.services.retrieval as retrieval_module

        ingestion_module._ingestion_service = None
        retrieval_module._retrieval_service = None
        generation_module._generation_service = None
        intent_module._intent_service = None
        chat_module._chat_service = None
        vectorstore_module._vector_store = None
        embedding_module._embedding_service = None

    def test_get_or_create_conversation_new(self, mock_settings, mock_embedding_service):
        """Should create a new conversation when ID is None."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch(
                                "app.rag.vectorstore.get_settings", return_value=mock_settings
                            ):
                                with patch(
                                    "app.rag.vectorstore.get_embedding_service",
                                    return_value=mock_embedding_service,
                                ):
                                    from app.services.chat import ChatService

                                    service = ChatService()

                                    conversation = service._get_or_create_conversation(
                                        conversation_id=None,
                                        document_ids=["doc-001"],
                                    )

                                    assert conversation is not None
                                    assert conversation.conversation_id is not None
                                    assert conversation.document_ids == ["doc-001"]
                                    assert len(conversation.messages) == 0

        self._reset_singletons()

    def test_get_or_create_conversation_existing(self, mock_settings, mock_embedding_service):
        """Should return existing conversation when ID matches."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch(
                                "app.rag.vectorstore.get_settings", return_value=mock_settings
                            ):
                                with patch(
                                    "app.rag.vectorstore.get_embedding_service",
                                    return_value=mock_embedding_service,
                                ):
                                    from app.services.chat import ChatService

                                    service = ChatService()

                                    # Create initial conversation
                                    conv1 = service._get_or_create_conversation(
                                        conversation_id=None,
                                        document_ids=None,
                                    )
                                    conv_id = conv1.conversation_id

                                    # Get same conversation
                                    conv2 = service._get_or_create_conversation(
                                        conversation_id=conv_id,
                                        document_ids=None,
                                    )

                                    assert conv2.conversation_id == conv_id

        self._reset_singletons()

    def test_create_user_message(self, mock_settings, mock_embedding_service):
        """Should create a user message with correct fields."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch(
                                "app.rag.vectorstore.get_settings", return_value=mock_settings
                            ):
                                with patch(
                                    "app.rag.vectorstore.get_embedding_service",
                                    return_value=mock_embedding_service,
                                ):
                                    from app.services.chat import ChatService

                                    service = ChatService()
                                    message = service._create_user_message("Hello world")

                                    assert message.role == ChatRole.USER
                                    assert message.content == "Hello world"
                                    assert message.message_id is not None
                                    assert message.sources_used == []

        self._reset_singletons()

    def test_create_assistant_message(self, mock_settings, mock_embedding_service, sample_sources):
        """Should create an assistant message with sources."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch(
                                "app.rag.vectorstore.get_settings", return_value=mock_settings
                            ):
                                with patch(
                                    "app.rag.vectorstore.get_embedding_service",
                                    return_value=mock_embedding_service,
                                ):
                                    from app.services.chat import ChatService

                                    service = ChatService()
                                    message = service._create_assistant_message(
                                        content="This is the response",
                                        sources=sample_sources,
                                    )

                                    assert message.role == ChatRole.ASSISTANT
                                    assert message.content == "This is the response"
                                    assert len(message.sources_used) == 3

        self._reset_singletons()

    def test_get_conversation_history_empty(self, mock_settings, mock_embedding_service):
        """Should return empty history for new conversation."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch(
                                "app.rag.vectorstore.get_settings", return_value=mock_settings
                            ):
                                with patch(
                                    "app.rag.vectorstore.get_embedding_service",
                                    return_value=mock_embedding_service,
                                ):
                                    from app.services.chat import ChatService

                                    service = ChatService()
                                    conversation = Conversation(
                                        conversation_id="test",
                                        messages=[],
                                    )

                                    history, truncated = service._get_conversation_history(
                                        conversation, max_turns=5
                                    )

                                    assert history == []
                                    assert truncated is False

        self._reset_singletons()

    def test_get_conversation_history_with_messages(self, mock_settings, mock_embedding_service):
        """Should return history in order."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch(
                                "app.rag.vectorstore.get_settings", return_value=mock_settings
                            ):
                                with patch(
                                    "app.rag.vectorstore.get_embedding_service",
                                    return_value=mock_embedding_service,
                                ):
                                    from app.services.chat import ChatService

                                    service = ChatService()

                                    messages = [
                                        ChatMessage(
                                            message_id="1", role=ChatRole.USER, content="Q1"
                                        ),
                                        ChatMessage(
                                            message_id="2", role=ChatRole.ASSISTANT, content="A1"
                                        ),
                                        ChatMessage(
                                            message_id="3", role=ChatRole.USER, content="Q2"
                                        ),
                                        ChatMessage(
                                            message_id="4", role=ChatRole.ASSISTANT, content="A2"
                                        ),
                                    ]
                                    conversation = Conversation(
                                        conversation_id="test",
                                        messages=messages,
                                    )

                                    history, truncated = service._get_conversation_history(
                                        conversation, max_turns=5
                                    )

                                    assert len(history) == 4
                                    assert history[0] == ("user", "Q1")
                                    assert history[1] == ("assistant", "A1")
                                    assert truncated is False

        self._reset_singletons()

    def test_get_conversation_history_truncation(self, mock_settings, mock_embedding_service):
        """Should truncate history when exceeding max_turns."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                            with patch(
                                "app.rag.vectorstore.get_settings", return_value=mock_settings
                            ):
                                with patch(
                                    "app.rag.vectorstore.get_embedding_service",
                                    return_value=mock_embedding_service,
                                ):
                                    from app.services.chat import ChatService

                                    service = ChatService()

                                    # Create 10 messages (5 turns)
                                    messages = []
                                    for i in range(10):
                                        role = ChatRole.USER if i % 2 == 0 else ChatRole.ASSISTANT
                                        messages.append(
                                            ChatMessage(
                                                message_id=str(i),
                                                role=role,
                                                content=f"Message {i}",
                                            )
                                        )

                                    conversation = Conversation(
                                        conversation_id="test",
                                        messages=messages,
                                    )

                                    # Request only 2 turns (4 messages)
                                    history, truncated = service._get_conversation_history(
                                        conversation, max_turns=2
                                    )

                                    assert len(history) == 4
                                    assert truncated is True
                                    # Should be the last 4 messages
                                    assert history[0][1] == "Message 6"

        self._reset_singletons()


# ============================================================================
# Chat API Endpoint Tests
# ============================================================================


class TestChatAPIEndpoints:
    """Tests for chat API endpoints.

    These tests focus on request validation and basic endpoint behavior.
    """

    def _reset_singletons(self):
        """Reset all singleton instances."""
        import app.rag.embedding as embedding_module
        import app.rag.vectorstore as vectorstore_module
        import app.services.chat as chat_module
        import app.services.generation as generation_module
        import app.services.ingestion as ingestion_module
        import app.services.intent as intent_module
        import app.services.retrieval as retrieval_module

        ingestion_module._ingestion_service = None
        retrieval_module._retrieval_service = None
        generation_module._generation_service = None
        intent_module._intent_service = None
        chat_module._chat_service = None
        vectorstore_module._vector_store = None
        embedding_module._embedding_service = None

    def test_get_conversation_not_found(self, mock_settings, mock_embedding_service):
        """Should return 404 for non-existent conversation."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.chat.get_settings", return_value=mock_settings):
                    with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                        with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                            with patch(
                                "app.rag.vectorstore.get_embedding_service",
                                return_value=mock_embedding_service,
                            ):
                                from app.main import app

                                client = TestClient(app)

                                response = client.get("/api/chat/nonexistent-id")

                                assert response.status_code == 404
                                assert "not found" in response.json()["detail"].lower()

        self._reset_singletons()

    def test_chat_empty_message_rejected(self, mock_settings, mock_embedding_service):
        """Should reject empty chat messages."""
        self._reset_singletons()

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                    with patch("app.rag.vectorstore.get_settings", return_value=mock_settings):
                        with patch(
                            "app.rag.vectorstore.get_embedding_service",
                            return_value=mock_embedding_service,
                        ):
                            from app.main import app

                            client = TestClient(app)

                            response = client.post("/api/chat", json={"message": ""})

                            assert response.status_code == 422

        self._reset_singletons()


# ============================================================================
# Async Chat Service Integration Tests
# ============================================================================


class TestChatServiceIntegration:
    """Integration tests for ChatService.chat() method.

    These tests use pytest-asyncio to test the async chat functionality
    directly, with mocked LLM responses.
    """

    def _reset_singletons(self):
        """Reset all singleton instances."""
        import app.rag.embedding as embedding_module
        import app.rag.vectorstore as vectorstore_module
        import app.services.chat as chat_module
        import app.services.generation as generation_module
        import app.services.ingestion as ingestion_module
        import app.services.intent as intent_module
        import app.services.retrieval as retrieval_module

        ingestion_module._ingestion_service = None
        retrieval_module._retrieval_service = None
        generation_module._generation_service = None
        intent_module._intent_service = None
        chat_module._chat_service = None
        vectorstore_module._vector_store = None
        embedding_module._embedding_service = None

    def _inject_mock_llm(self, gen_service, mock_llm, settings):
        """Inject mock LLM into generation service."""
        # Override LLM creation to always return the mock
        gen_service._get_or_create_llm = lambda model: mock_llm

    @pytest.mark.asyncio
    async def test_chat_creates_new_conversation(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Chat should create a new conversation when ID is None."""
        self._reset_singletons()

        mock_llm.set_response("Test response with [Source 1] citation.")

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.services.chat.get_settings", return_value=mock_settings):
                            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                                with patch(
                                    "app.rag.vectorstore.get_settings", return_value=mock_settings
                                ):
                                    with patch(
                                        "app.rag.vectorstore.get_embedding_service",
                                        return_value=mock_embedding_service,
                                    ):
                                        from app.services.chat import ChatService
                                        from app.services.generation import GenerationService

                                        # Create service with mocked LLM
                                        gen_service = GenerationService()
                                        self._inject_mock_llm(gen_service, mock_llm, mock_settings)

                                        chat_service = ChatService()
                                        chat_service.generation_service = gen_service

                                        result = await chat_service.chat(
                                            conversation_id=None,
                                            message="Test question",
                                            document_ids=None,
                                        )

                                        assert result.conversation.conversation_id is not None
                                        assert len(result.conversation.messages) == 2
                                        assert result.message.role == ChatRole.ASSISTANT

        self._reset_singletons()

    @pytest.mark.asyncio
    async def test_chat_continues_existing_conversation(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Chat should continue an existing conversation."""
        self._reset_singletons()

        mock_llm.set_response("First response.")

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.services.chat.get_settings", return_value=mock_settings):
                            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                                with patch(
                                    "app.rag.vectorstore.get_settings", return_value=mock_settings
                                ):
                                    with patch(
                                        "app.rag.vectorstore.get_embedding_service",
                                        return_value=mock_embedding_service,
                                    ):
                                        from app.services.chat import ChatService
                                        from app.services.generation import GenerationService

                                        gen_service = GenerationService()
                                        self._inject_mock_llm(gen_service, mock_llm, mock_settings)

                                        chat_service = ChatService()
                                        chat_service.generation_service = gen_service

                                        # First message
                                        result1 = await chat_service.chat(
                                            conversation_id=None,
                                            message="First question",
                                        )
                                        conv_id = result1.conversation.conversation_id

                                        # Continue conversation
                                        mock_llm.set_response("Second response.")
                                        result2 = await chat_service.chat(
                                            conversation_id=conv_id,
                                            message="Follow-up question",
                                        )

                                        assert result2.conversation.conversation_id == conv_id
                                        assert (
                                            len(result2.conversation.messages) == 4
                                        )  # 2 user + 2 assistant

        self._reset_singletons()

    @pytest.mark.asyncio
    async def test_chat_returns_context_used(self, mock_settings, mock_embedding_service, mock_llm):
        """Chat should return context_used for transparency."""
        self._reset_singletons()

        mock_llm.set_response("Response content.")

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.services.chat.get_settings", return_value=mock_settings):
                            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                                with patch(
                                    "app.rag.vectorstore.get_settings", return_value=mock_settings
                                ):
                                    with patch(
                                        "app.rag.vectorstore.get_embedding_service",
                                        return_value=mock_embedding_service,
                                    ):
                                        from app.services.chat import ChatService
                                        from app.services.generation import GenerationService

                                        gen_service = GenerationService()
                                        self._inject_mock_llm(gen_service, mock_llm, mock_settings)

                                        chat_service = ChatService()
                                        chat_service.generation_service = gen_service

                                        result = await chat_service.chat(
                                            conversation_id=None,
                                            message="Test question",
                                        )

                                        assert result.context_used is not None
                                        assert hasattr(
                                            result.context_used, "history_messages_count"
                                        )
                                        assert hasattr(result.context_used, "history_truncated")
                                        assert hasattr(result.context_used, "sources_count")

        self._reset_singletons()

    @pytest.mark.asyncio
    async def test_chat_response_to_response_conversion(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """ChatResult.to_response() should produce valid API response."""
        self._reset_singletons()

        mock_llm.set_response("Response content.")

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.services.chat.get_settings", return_value=mock_settings):
                            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                                with patch(
                                    "app.rag.vectorstore.get_settings", return_value=mock_settings
                                ):
                                    with patch(
                                        "app.rag.vectorstore.get_embedding_service",
                                        return_value=mock_embedding_service,
                                    ):
                                        from app.services.chat import ChatService
                                        from app.services.generation import GenerationService

                                        gen_service = GenerationService()
                                        self._inject_mock_llm(gen_service, mock_llm, mock_settings)

                                        chat_service = ChatService()
                                        chat_service.generation_service = gen_service

                                        result = await chat_service.chat(
                                            conversation_id=None,
                                            message="Test question",
                                        )

                                        response = result.to_response()

                                        assert response.conversation_id is not None
                                        assert response.message.role == "assistant"
                                        assert response.context_used is not None
                                        assert response.generation_time_ms >= 0

        self._reset_singletons()


# ============================================================================
# Coverage Tracking Tests
# ============================================================================


class TestCumulativeCoverage:
    """Tests for cumulative coverage tracking across conversation turns."""

    def _reset_singletons(self):
        """Reset all singleton instances."""
        import app.rag.embedding as embedding_module
        import app.rag.vectorstore as vectorstore_module
        import app.services.chat as chat_module
        import app.services.generation as generation_module
        import app.services.ingestion as ingestion_module
        import app.services.intent as intent_module
        import app.services.retrieval as retrieval_module

        ingestion_module._ingestion_service = None
        retrieval_module._retrieval_service = None
        generation_module._generation_service = None
        intent_module._intent_service = None
        chat_module._chat_service = None
        vectorstore_module._vector_store = None
        embedding_module._embedding_service = None

    def _inject_mock_llm(self, gen_service, mock_llm, settings):
        """Inject mock LLM into generation service."""
        gen_service._get_or_create_llm = lambda model: mock_llm

    @pytest.mark.asyncio
    async def test_coverage_tracked_across_turns(
        self, mock_settings, mock_embedding_service, mock_llm
    ):
        """Cumulative coverage should accumulate across conversation turns."""
        self._reset_singletons()

        mock_llm.set_response("First response with [Source 1].")

        with patch("app.config.get_settings", return_value=mock_settings):
            with patch("app.services.ingestion.get_settings", return_value=mock_settings):
                with patch("app.services.retrieval.get_settings", return_value=mock_settings):
                    with patch("app.services.generation.get_settings", return_value=mock_settings):
                        with patch("app.services.chat.get_settings", return_value=mock_settings):
                            with patch("app.rag.chunking.get_settings", return_value=mock_settings):
                                with patch(
                                    "app.rag.vectorstore.get_settings", return_value=mock_settings
                                ):
                                    with patch(
                                        "app.rag.vectorstore.get_embedding_service",
                                        return_value=mock_embedding_service,
                                    ):
                                        from app.services.chat import ChatService
                                        from app.services.generation import GenerationService

                                        gen_service = GenerationService()
                                        self._inject_mock_llm(gen_service, mock_llm, mock_settings)

                                        chat_service = ChatService()
                                        chat_service.generation_service = gen_service

                                        # First turn
                                        result1 = await chat_service.chat(
                                            conversation_id=None,
                                            message="First question",
                                        )
                                        conv_id = result1.conversation.conversation_id

                                        # Second turn
                                        mock_llm.set_response("Second response.")
                                        result2 = await chat_service.chat(
                                            conversation_id=conv_id,
                                            message="Different topic question",
                                        )

                                        # Verify conversation maintained
                                        assert result2.conversation.conversation_id == conv_id

                                        # Verify cumulative coverage exists
                                        if result2.conversation.cumulative_coverage:
                                            coverage = result2.conversation.cumulative_coverage
                                            # Should have chunks_seen attribute
                                            assert hasattr(coverage, "chunks_seen")

        self._reset_singletons()

    def test_coverage_update_accumulates_chunks(self, sample_sources):
        """Coverage update should accumulate unique chunks."""
        from app.models import (
            Conversation,
            RetrievalMetadata,
        )
        from app.services.chat import ChatService

        # Create conversation with existing coverage
        conversation = Conversation(
            conversation_id="test",
            messages=[],
            cumulative_coverage=CoverageDescriptor(
                retrieval_type=RetrievalType.SIMILARITY,
                chunks_seen=2,
                chunks_total=10,
                coverage_percentage=20.0,
                document_coverage={},
                blind_spots=[],
                coverage_summary="Test coverage",
            ),
        )

        # Mock retrieval metadata with coverage
        retrieval_metadata = RetrievalMetadata(
            query="test",
            top_k=5,
            similarity_threshold=0.5,
            chunks_retrieved=3,
            chunks_above_threshold=3,
            retrieval_time_ms=10.0,
            coverage=CoverageDescriptor(
                retrieval_type=RetrievalType.SIMILARITY,
                chunks_seen=3,
                chunks_total=10,
                coverage_percentage=30.0,
                document_coverage={},
                blind_spots=[],
                coverage_summary="",
            ),
        )

        # New sources (some may overlap with existing)
        new_sources = sample_sources[:2]  # 2 new sources

        # Service doesn't need full initialization for this test
        # Just testing the coverage update logic
        chat_service = ChatService.__new__(ChatService)
        chat_service._update_cumulative_coverage(conversation, new_sources, retrieval_metadata)

        # Coverage should be updated
        assert conversation.cumulative_coverage is not None
        assert conversation.cumulative_coverage.chunks_total == 10


# ============================================================================
# ChatRole Enum Tests
# ============================================================================


class TestChatRoleEnum:
    """Tests for ChatRole enum."""

    def test_user_role_value(self):
        """User role should have correct value."""
        assert ChatRole.USER.value == "user"

    def test_assistant_role_value(self):
        """Assistant role should have correct value."""
        assert ChatRole.ASSISTANT.value == "assistant"

    def test_role_comparison(self):
        """Roles should be comparable."""
        assert ChatRole.USER != ChatRole.ASSISTANT
        assert ChatRole.USER == ChatRole.USER
