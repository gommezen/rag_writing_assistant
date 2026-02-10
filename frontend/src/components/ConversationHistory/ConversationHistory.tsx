/**
 * ConversationHistory component for displaying and managing past conversations.
 *
 * Shows in the sidebar when in chat mode, allowing users to:
 * - Start a new chat
 * - View past conversations
 * - Resume a previous conversation
 * - Delete conversations
 * - Edit conversation titles
 */

import { useState, useRef, useEffect } from 'react';
import { MessageSquare, Trash2, Plus, Clock, Pencil } from 'lucide-react';
import { ConversationHistorySkeleton } from '../Skeleton/Skeleton';
import type { ConversationSummary } from '../../types';
import './ConversationHistory.css';

interface ConversationHistoryProps {
  conversations: ConversationSummary[];
  currentConversationId: string | null;
  onSelect: (conversationId: string) => void;
  onDelete: (conversationId: string) => void;
  onUpdateTitle: (conversationId: string, title: string) => void;
  onNewChat: () => void;
  isLoading: boolean;
}

export function ConversationHistory({
  conversations,
  currentConversationId,
  onSelect,
  onDelete,
  onUpdateTitle,
  onNewChat,
  isLoading,
}: ConversationHistoryProps) {
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const editInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingId]);

  const handleStartEdit = (e: React.MouseEvent, conversationId: string, currentTitle: string) => {
    e.stopPropagation();
    setEditingId(conversationId);
    setEditingTitle(currentTitle);
  };

  const handleSaveEdit = (conversationId: string) => {
    const trimmed = editingTitle.trim();
    if (trimmed && trimmed !== conversations.find((c) => c.conversation_id === conversationId)?.title) {
      onUpdateTitle(conversationId, trimmed);
    }
    setEditingId(null);
    setEditingTitle('');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditingTitle('');
  };

  const handleEditKeyDown = (e: React.KeyboardEvent, conversationId: string) => {
    if (e.key === 'Enter') {
      handleSaveEdit(conversationId);
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  const handleDelete = (e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation();
    if (deleteConfirm === conversationId) {
      onDelete(conversationId);
      setDeleteConfirm(null);
    } else {
      setDeleteConfirm(conversationId);
      // Auto-cancel after 3 seconds
      setTimeout(() => setDeleteConfirm(null), 3000);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (days === 1) {
      return 'Yesterday';
    } else if (days < 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  return (
    <div className="conversation-history">
      <button
        type="button"
        className="conversation-history__new-btn"
        onClick={onNewChat}
      >
        <Plus size={16} />
        New Chat
      </button>

      {isLoading ? (
        <ConversationHistorySkeleton />
      ) : conversations.length === 0 ? (
        <div className="conversation-history__empty">
          <MessageSquare size={24} />
          <p>No conversations yet</p>
          <span>Start a new chat to ask questions about your documents</span>
        </div>
      ) : (
        <ul className="conversation-history__list">
          {conversations.map((conv) => (
            <li
              key={conv.conversation_id}
              className={`conversation-history__item ${
                currentConversationId === conv.conversation_id
                  ? 'conversation-history__item--active'
                  : ''
              }`}
              onClick={() => onSelect(conv.conversation_id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  onSelect(conv.conversation_id);
                }
              }}
            >
              <div className="conversation-history__item-content">
                {editingId === conv.conversation_id ? (
                  <input
                    ref={editInputRef}
                    type="text"
                    className="conversation-history__title-input"
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onBlur={() => handleSaveEdit(conv.conversation_id)}
                    onKeyDown={(e) => handleEditKeyDown(e, conv.conversation_id)}
                    onClick={(e) => e.stopPropagation()}
                    maxLength={200}
                  />
                ) : (
                  <div className="conversation-history__title-row">
                    <span className="conversation-history__title">{conv.title}</span>
                    <button
                      type="button"
                      className="conversation-history__edit"
                      onClick={(e) => handleStartEdit(e, conv.conversation_id, conv.title)}
                      aria-label="Edit title"
                    >
                      <Pencil size={12} />
                    </button>
                  </div>
                )}
                <span className="conversation-history__meta">
                  <Clock size={12} />
                  {formatTimestamp(conv.updated_at)}
                  <span className="conversation-history__count">
                    {conv.message_count} msg{conv.message_count !== 1 ? 's' : ''}
                  </span>
                </span>
              </div>
              <button
                type="button"
                className={`conversation-history__delete ${
                  deleteConfirm === conv.conversation_id
                    ? 'conversation-history__delete--confirm'
                    : ''
                }`}
                onClick={(e) => handleDelete(e, conv.conversation_id)}
                aria-label={
                  deleteConfirm === conv.conversation_id
                    ? 'Click again to confirm delete'
                    : `Delete conversation: ${conv.title}`
                }
              >
                <Trash2 size={14} />
                {deleteConfirm === conv.conversation_id && <span>Confirm?</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
