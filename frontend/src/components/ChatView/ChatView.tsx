/**
 * ChatView - main container for chat mode.
 *
 * Displays the message thread with coverage info and input at the bottom.
 */

import { useRef, useEffect } from 'react';
import { MessageSquare, Info } from 'lucide-react';
import type { ChatMessage as ChatMessageType, CoverageDescriptor, ContextUsed } from '../../types';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { ChatProgress } from '../Skeleton/Skeleton';
import './ChatView.css';

interface ChatViewProps {
  messages: ChatMessageType[];
  cumulativeCoverage: CoverageDescriptor | null;
  lastContextUsed: ContextUsed | null;
  isLoading: boolean;
  onSendMessage: (message: string) => void;
  documentCount: number;
}

export function ChatView({
  messages,
  cumulativeCoverage,
  lastContextUsed,
  isLoading,
  onSendMessage,
  documentCount,
}: ChatViewProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const hasDocuments = documentCount > 0;

  return (
    <div className="chat-view">
      {/* Coverage info bar */}
      {cumulativeCoverage && (
        <div className="chat-view__coverage">
          <Info size={16} />
          <span>
            Conversation coverage: {cumulativeCoverage.chunks_seen} of{' '}
            {cumulativeCoverage.chunks_total} chunks (~
            {cumulativeCoverage.coverage_percentage.toFixed(0)}%)
          </span>
          {lastContextUsed && (
            <span className="chat-view__context-info">
              Last turn: {lastContextUsed.sources_count} sources,{' '}
              {lastContextUsed.history_messages_count} history messages
              {lastContextUsed.history_truncated && ' (truncated)'}
            </span>
          )}
        </div>
      )}

      {/* Message thread */}
      <div className="chat-view__messages">
        {messages.length === 0 ? (
          <div className="chat-view__empty">
            <MessageSquare size={48} strokeWidth={1.5} />
            <h3>Start a conversation</h3>
            <p>
              {hasDocuments
                ? 'Ask questions about your documents. Follow-up questions will build on prior context.'
                : 'Upload documents first, then ask questions about them.'}
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <ChatMessage key={message.message_id} message={message} />
            ))}
            {isLoading && (
              <div className="chat-view__loading">
                <ChatProgress />
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <ChatInput
        onSend={onSendMessage}
        disabled={isLoading || !hasDocuments}
        placeholder={
          hasDocuments
            ? 'Ask a question about your documents...'
            : 'Upload documents to start chatting'
        }
      />
    </div>
  );
}
