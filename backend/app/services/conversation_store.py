"""Conversation persistence service.

Provides file-based storage for chat conversations, following the same
pattern as the document registry for consistency and auditability.

Storage layout:
    data/conversations/
    ├── conversations.json       # Lightweight index (id, title, timestamps)
    └── {conversation_id}.json   # Full conversation data per file
"""

import json
from pathlib import Path

from ..core import get_logger
from ..models.chat import Conversation, ConversationSummary

logger = get_logger(__name__)


class ConversationStore:
    """File-based conversation persistence.

    Maintains a lightweight index for fast listing and individual
    files for full conversation data. Auto-saves after modifications.
    """

    def __init__(self, conversations_dir: Path):
        """Initialize the conversation store.

        Args:
            conversations_dir: Directory to store conversation files
        """
        self.conversations_dir = conversations_dir
        self.index_file = conversations_dir / "conversations.json"
        self._index: dict[str, ConversationSummary] = {}
        self._ensure_directory()
        self._load_index()

    def _ensure_directory(self) -> None:
        """Create storage directory if it doesn't exist."""
        self.conversations_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> None:
        """Load conversation index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        summary = ConversationSummary.from_dict(item)
                        self._index[summary.conversation_id] = summary
                logger.info(
                    "Loaded conversation index",
                    conversation_count=len(self._index),
                )
            except Exception as e:
                logger.warning("Failed to load conversation index", error=str(e))
                self._index = {}

    def _save_index(self) -> None:
        """Save conversation index to disk."""
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                data = [summary.to_dict() for summary in self._index.values()]
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save conversation index", error=str(e))

    def _get_conversation_path(self, conversation_id: str) -> Path:
        """Get file path for a conversation."""
        return self.conversations_dir / f"{conversation_id}.json"

    def save_conversation(self, conversation: Conversation) -> None:
        """Save full conversation and update index.

        Args:
            conversation: The conversation to save
        """
        try:
            # Save full conversation to individual file
            conv_path = self._get_conversation_path(conversation.conversation_id)
            with open(conv_path, "w", encoding="utf-8") as f:
                json.dump(conversation.to_dict(), f, indent=2)

            # Update index
            summary = ConversationSummary.from_conversation(conversation)
            self._index[conversation.conversation_id] = summary
            self._save_index()

            logger.debug(
                "Saved conversation",
                conversation_id=conversation.conversation_id,
                message_count=len(conversation.messages),
            )
        except Exception as e:
            logger.error(
                "Failed to save conversation",
                conversation_id=conversation.conversation_id,
                error=str(e),
            )
            raise

    def load_conversation(self, conversation_id: str) -> Conversation | None:
        """Load full conversation from disk.

        Args:
            conversation_id: The conversation ID to load

        Returns:
            The loaded conversation, or None if not found
        """
        conv_path = self._get_conversation_path(conversation_id)
        if not conv_path.exists():
            logger.debug(
                "Conversation file not found",
                conversation_id=conversation_id,
            )
            return None

        try:
            with open(conv_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Conversation.from_dict(data)
        except Exception as e:
            logger.error(
                "Failed to load conversation",
                conversation_id=conversation_id,
                error=str(e),
            )
            return None

    def list_conversations(self) -> list[ConversationSummary]:
        """List all conversations sorted by updated_at (newest first).

        Returns:
            List of conversation summaries
        """
        summaries = list(self._index.values())
        summaries.sort(key=lambda s: s.updated_at, reverse=True)
        return summaries

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation file and remove from index.

        Args:
            conversation_id: The conversation ID to delete

        Returns:
            True if deleted, False if not found
        """
        if conversation_id not in self._index:
            return False

        try:
            # Remove from index
            del self._index[conversation_id]
            self._save_index()

            # Delete file
            conv_path = self._get_conversation_path(conversation_id)
            if conv_path.exists():
                conv_path.unlink()

            logger.info(
                "Deleted conversation",
                conversation_id=conversation_id,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to delete conversation",
                conversation_id=conversation_id,
                error=str(e),
            )
            return False

    def update_title(self, conversation_id: str, title: str) -> bool:
        """Update conversation title in index.

        Args:
            conversation_id: The conversation ID to update
            title: New title for the conversation

        Returns:
            True if updated, False if not found
        """
        if conversation_id not in self._index:
            return False

        try:
            self._index[conversation_id].title = title
            self._save_index()

            logger.debug(
                "Updated conversation title",
                conversation_id=conversation_id,
                title=title,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to update conversation title",
                conversation_id=conversation_id,
                error=str(e),
            )
            return False

    def exists(self, conversation_id: str) -> bool:
        """Check if a conversation exists.

        Args:
            conversation_id: The conversation ID to check

        Returns:
            True if the conversation exists
        """
        return conversation_id in self._index

    def get_summary(self, conversation_id: str) -> ConversationSummary | None:
        """Get conversation summary without loading full conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            The conversation summary, or None if not found
        """
        return self._index.get(conversation_id)
