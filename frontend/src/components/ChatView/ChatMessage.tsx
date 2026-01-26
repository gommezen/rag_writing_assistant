/**
 * ChatMessage - displays a single message in the chat thread.
 *
 * User messages are simple bubbles.
 * Assistant messages show content with inline source badges and expandable details.
 * Citations in assistant messages are interactive - hover for preview, click to scroll to source.
 */

import { useState, useRef, useCallback } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../../types';
import { SourceCard } from '../SourceCard';
import { renderCitationsInText } from '../../utils/citationParser';
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
  const [highlightedSourceIndex, setHighlightedSourceIndex] = useState<number | null>(null);
  const isUser = message.role === 'user';

  // Refs for source cards to enable scroll-to-source
  const sourceRefs = useRef<Map<number, HTMLElement>>(new Map());

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const handleCitationClick = useCallback((index: number) => {
    // Auto-expand sources panel if not already open
    if (!showSources) {
      setShowSources(true);
      // Small delay to let DOM update before scrolling
      setTimeout(() => {
        scrollToAndHighlight(index);
      }, 100);
    } else {
      scrollToAndHighlight(index);
    }
  }, [showSources]);

  const scrollToAndHighlight = (index: number) => {
    // Highlight the source card
    setHighlightedSourceIndex(index);

    // Scroll to the source card
    const sourceRef = sourceRefs.current.get(index);
    if (sourceRef) {
      sourceRef.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // Clear highlight after animation
    setTimeout(() => setHighlightedSourceIndex(null), 2000);
  };

  const setSourceRef = useCallback(
    (index: number) => (el: HTMLElement | null) => {
      if (el) {
        sourceRefs.current.set(index, el);
      } else {
        sourceRefs.current.delete(index);
      }
    },
    []
  );

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
          {renderCitationsInText(message.content, message.sources_used, handleCitationClick)}
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
              <SourceCard
                key={source.chunk_id}
                ref={setSourceRef(idx + 1)}
                source={source}
                index={idx + 1}
                isHighlighted={highlightedSourceIndex === idx + 1}
              />
            ))}
          </div>
        )}

        <span className="chat-message__timestamp">{formatTimestamp(message.timestamp)}</span>
      </div>
    </div>
  );
}
