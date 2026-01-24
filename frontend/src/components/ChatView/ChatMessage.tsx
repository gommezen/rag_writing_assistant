/**
 * ChatMessage - displays a single message in the chat thread.
 *
 * User messages are simple bubbles.
 * Assistant messages show content with inline source badges and expandable details.
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../../types';
import { SourceCard } from '../SourceCard';
import './ChatMessage.css';

interface ChatMessageProps {
  message: ChatMessageType;
  isSelected?: boolean;
  onSelect?: () => void;
}

export function ChatMessage({
  message,
  isSelected = false,
  onSelect,
}: ChatMessageProps) {
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === 'user';

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (isUser) {
    return (
      <div className="chat-message chat-message--user">
        <div className="chat-message__bubble chat-message__bubble--user">
          <p className="chat-message__content">{message.content}</p>
          <span className="chat-message__timestamp">{formatTimestamp(message.timestamp)}</span>
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div
      className={`chat-message chat-message--assistant ${isSelected ? 'chat-message--selected' : ''}`}
      onClick={onSelect}
    >
      <div className="chat-message__bubble chat-message__bubble--assistant">
        <div className="chat-message__content chat-message__content--assistant">
          {message.content}
        </div>

        {message.sources_used.length > 0 && (
          <div className="chat-message__sources-toggle">
            <button
              className="chat-message__sources-button"
              onClick={(e) => {
                e.stopPropagation();
                setShowSources(!showSources);
              }}
            >
              {showSources ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              {message.sources_used.length} source{message.sources_used.length !== 1 ? 's' : ''}
            </button>
          </div>
        )}

        {showSources && message.sources_used.length > 0 && (
          <div className="chat-message__sources">
            {message.sources_used.map((source, idx) => (
              <SourceCard key={source.chunk_id} source={source} index={idx + 1} />
            ))}
          </div>
        )}

        <span className="chat-message__timestamp">{formatTimestamp(message.timestamp)}</span>
      </div>
    </div>
  );
}
