"""Chat-related request and response models.

These models define the API contracts for multi-turn conversation endpoints.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

from .common import (
    CoverageDescriptor,
    GeneratedSection,
    SourceReference,
)
from .generation import (
    CoverageDescriptorResponse,
    GeneratedSectionResponse,
    SourceReferenceResponse,
)


class ChatRole(str, Enum):
    """Role of a message in the conversation."""

    USER = "user"
    ASSISTANT = "assistant"


# Internal dataclasses for service layer


@dataclass
class ChatMessage:
    """A single message in a conversation.

    For user messages: content is the user's input
    For assistant messages: content is the response, with optional sections
    """

    message_id: str
    role: ChatRole
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    sections: list[GeneratedSection] | None = None  # Assistant messages only
    sources_used: list[SourceReference] = field(default_factory=list)

    def to_dict(self) -> dict:
        result = {
            "message_id": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "sources_used": [s.to_dict() for s in self.sources_used],
        }
        if self.sections:
            result["sections"] = [s.to_dict() for s in self.sections]
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        """Create ChatMessage from dictionary (for deserialization)."""
        from datetime import datetime

        sections = None
        if data.get("sections"):
            sections = [GeneratedSection.from_dict(s) for s in data["sections"]]
        return cls(
            message_id=data["message_id"],
            role=ChatRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            sections=sections,
            sources_used=[SourceReference.from_dict(s) for s in data.get("sources_used", [])],
        )


@dataclass
class Conversation:
    """A conversation thread with message history.

    Conversations are scoped to specific documents (or all documents if None).
    Cumulative coverage tracks what has been retrieved across all turns.
    """

    conversation_id: str
    messages: list[ChatMessage] = field(default_factory=list)
    document_ids: list[str] | None = None  # None = all documents
    cumulative_coverage: CoverageDescriptor | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "messages": [m.to_dict() for m in self.messages],
            "document_ids": self.document_ids,
            "cumulative_coverage": self.cumulative_coverage.to_dict()
            if self.cumulative_coverage
            else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        """Create Conversation from dictionary (for deserialization)."""
        from datetime import datetime

        cumulative_coverage = None
        if data.get("cumulative_coverage"):
            cumulative_coverage = CoverageDescriptor.from_dict(data["cumulative_coverage"])
        return cls(
            conversation_id=data["conversation_id"],
            messages=[ChatMessage.from_dict(m) for m in data.get("messages", [])],
            document_ids=data.get("document_ids"),
            cumulative_coverage=cumulative_coverage,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class ConversationSummary:
    """Lightweight summary of a conversation for listing.

    Used in the conversation index to avoid loading full conversation data.
    """

    conversation_id: str
    title: str  # First user message, truncated
    message_count: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationSummary":
        """Create ConversationSummary from dictionary."""
        from datetime import datetime

        return cls(
            conversation_id=data["conversation_id"],
            title=data["title"],
            message_count=data["message_count"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    @classmethod
    def from_conversation(
        cls, conversation: "Conversation", max_title_length: int = 50
    ) -> "ConversationSummary":
        """Create summary from a full Conversation."""
        # Find first user message for title
        title = "New conversation"
        for msg in conversation.messages:
            if msg.role == ChatRole.USER:
                title = msg.content[:max_title_length]
                if len(msg.content) > max_title_length:
                    title += "..."
                break
        return cls(
            conversation_id=conversation.conversation_id,
            title=title,
            message_count=len(conversation.messages),
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )


# Pydantic models for API request/response validation


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    conversation_id: str | None = Field(
        default=None,
        description="Conversation ID to continue. If None, starts a new conversation.",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The user's message",
    )
    document_ids: list[str] | None = Field(
        default=None,
        description="Specific documents to use. If None, uses all documents.",
    )
    include_history: bool = Field(
        default=True,
        description="Whether to include conversation history in LLM context",
    )
    history_turns: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of prior turns to include in context",
    )

    model_config = {"extra": "forbid"}


class ChatMessageResponse(BaseModel):
    """API response model for a chat message."""

    message_id: str
    role: str
    content: str
    timestamp: str
    sections: list[GeneratedSectionResponse] | None = None
    sources_used: list[SourceReferenceResponse] = Field(default_factory=list)

    @classmethod
    def from_dataclass(cls, message: ChatMessage) -> "ChatMessageResponse":
        return cls(
            message_id=message.message_id,
            role=message.role.value,
            content=message.content,
            timestamp=message.timestamp.isoformat(),
            sections=[GeneratedSectionResponse.from_dataclass(s) for s in message.sections]
            if message.sections
            else None,
            sources_used=[SourceReferenceResponse.from_dataclass(s) for s in message.sources_used],
        )


class ContextUsedResponse(BaseModel):
    """Shows what context was sent to the LLM for transparency."""

    history_messages_count: int = Field(description="Number of prior messages included")
    history_truncated: bool = Field(description="Whether history was truncated due to length")
    sources_count: int = Field(description="Number of sources retrieved for this turn")


class ChatResponse(BaseModel):
    """Response from a chat turn."""

    conversation_id: str
    message: ChatMessageResponse
    cumulative_coverage: CoverageDescriptorResponse | None = None
    context_used: ContextUsedResponse
    generation_time_ms: float
    model_used: str

    model_config = {"extra": "forbid"}


class ConversationResponse(BaseModel):
    """Full conversation with all messages."""

    conversation_id: str
    messages: list[ChatMessageResponse]
    document_ids: list[str] | None = None
    cumulative_coverage: CoverageDescriptorResponse | None = None
    created_at: str
    updated_at: str

    @classmethod
    def from_dataclass(cls, conversation: Conversation) -> "ConversationResponse":
        return cls(
            conversation_id=conversation.conversation_id,
            messages=[ChatMessageResponse.from_dataclass(m) for m in conversation.messages],
            document_ids=conversation.document_ids,
            cumulative_coverage=CoverageDescriptorResponse.from_dataclass(
                conversation.cumulative_coverage
            )
            if conversation.cumulative_coverage
            else None,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
        )

    model_config = {"extra": "forbid"}


class ConversationSummaryResponse(BaseModel):
    """API response model for conversation summary (used in listings)."""

    conversation_id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str

    @classmethod
    def from_dataclass(cls, summary: ConversationSummary) -> "ConversationSummaryResponse":
        return cls(
            conversation_id=summary.conversation_id,
            title=summary.title,
            message_count=summary.message_count,
            created_at=summary.created_at.isoformat(),
            updated_at=summary.updated_at.isoformat(),
        )

    model_config = {"extra": "forbid"}


# Internal result dataclass


@dataclass
class ChatResult:
    """Internal result from chat service."""

    conversation: Conversation
    message: ChatMessage
    context_used: ContextUsedResponse
    generation_time_ms: float
    model_used: str

    def to_response(self) -> ChatResponse:
        """Convert to API response model."""
        return ChatResponse(
            conversation_id=self.conversation.conversation_id,
            message=ChatMessageResponse.from_dataclass(self.message),
            cumulative_coverage=CoverageDescriptorResponse.from_dataclass(
                self.conversation.cumulative_coverage
            )
            if self.conversation.cumulative_coverage
            else None,
            context_used=self.context_used,
            generation_time_ms=self.generation_time_ms,
            model_used=self.model_used,
        )
