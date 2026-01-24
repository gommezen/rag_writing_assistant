/**
 * Tests for ChatMessage component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatMessage } from './ChatMessage';
import { createMockChatMessage, createMockAssistantMessage } from '../../test/mocks';

describe('ChatMessage', () => {
  describe('User messages', () => {
    it('renders user message with content', () => {
      const message = createMockChatMessage({
        role: 'user',
        content: 'What is this document about?',
      });

      render(<ChatMessage message={message} />);

      expect(screen.getByText('What is this document about?')).toBeInTheDocument();
    });

    it('renders user message with correct styling class', () => {
      const message = createMockChatMessage({ role: 'user' });

      const { container } = render(<ChatMessage message={message} />);

      expect(container.querySelector('.chat-message--user')).toBeInTheDocument();
    });

    it('displays formatted timestamp', () => {
      const timestamp = '2024-01-15T14:30:00Z';
      const message = createMockChatMessage({
        role: 'user',
        timestamp,
      });

      render(<ChatMessage message={message} />);

      // The exact format depends on locale (may use : or . as separator)
      const timestampElement = screen.getByText(/\d{1,2}[:.]\d{2}/);
      expect(timestampElement).toBeInTheDocument();
    });
  });

  describe('Assistant messages', () => {
    it('renders assistant message with content', () => {
      const message = createMockAssistantMessage({
        content: 'Here is the answer to your question.',
      });

      render(<ChatMessage message={message} />);

      expect(screen.getByText('Here is the answer to your question.')).toBeInTheDocument();
    });

    it('renders assistant message with correct styling class', () => {
      const message = createMockAssistantMessage();

      const { container } = render(<ChatMessage message={message} />);

      expect(container.querySelector('.chat-message--assistant')).toBeInTheDocument();
    });

    it('shows source count button when sources exist', () => {
      const message = createMockAssistantMessage();

      render(<ChatMessage message={message} />);

      expect(screen.getByText(/\d+ source/)).toBeInTheDocument();
    });

    it('does not show source button when no sources', () => {
      const message = createMockAssistantMessage({
        sources_used: [],
      });

      render(<ChatMessage message={message} />);

      expect(screen.queryByText(/\d+ source/)).not.toBeInTheDocument();
    });

    it('toggles source visibility on button click', () => {
      const message = createMockAssistantMessage();

      render(<ChatMessage message={message} />);

      // Sources should be hidden initially
      expect(screen.queryByText('[Source 1]')).not.toBeInTheDocument();

      // Click to show sources
      const toggleButton = screen.getByText(/\d+ source/);
      fireEvent.click(toggleButton);

      // Sources should now be visible
      expect(screen.getByText('[Source 1]')).toBeInTheDocument();

      // Click again to hide
      fireEvent.click(toggleButton);

      // Sources should be hidden again
      expect(screen.queryByText('[Source 1]')).not.toBeInTheDocument();
    });

    it('displays correct source count label (singular)', () => {
      const message = createMockAssistantMessage({
        sources_used: [
          {
            document_id: 'doc-1',
            chunk_id: 'chunk-1',
            excerpt: 'Test excerpt',
            relevance_score: 0.9,
            metadata: { title: 'Test' },
          },
        ],
      });

      render(<ChatMessage message={message} />);

      expect(screen.getByText('1 source')).toBeInTheDocument();
    });

    it('displays correct source count label (plural)', () => {
      const message = createMockAssistantMessage();

      render(<ChatMessage message={message} />);

      expect(screen.getByText(/\d+ sources/)).toBeInTheDocument();
    });
  });

  describe('Selection behavior', () => {
    it('applies selected class when isSelected is true', () => {
      const message = createMockAssistantMessage();

      const { container } = render(<ChatMessage message={message} isSelected={true} />);

      expect(container.querySelector('.chat-message--selected')).toBeInTheDocument();
    });

    it('does not apply selected class when isSelected is false', () => {
      const message = createMockAssistantMessage();

      const { container } = render(<ChatMessage message={message} isSelected={false} />);

      expect(container.querySelector('.chat-message--selected')).not.toBeInTheDocument();
    });

    it('calls onSelect when assistant message is clicked', () => {
      const message = createMockAssistantMessage();
      const handleSelect = vi.fn();

      render(<ChatMessage message={message} onSelect={handleSelect} />);

      const messageElement = screen.getByText(message.content).closest('.chat-message');
      fireEvent.click(messageElement!);

      expect(handleSelect).toHaveBeenCalledTimes(1);
    });

    it('does not call onSelect for user messages', () => {
      const message = createMockChatMessage({ role: 'user' });
      const handleSelect = vi.fn();

      render(<ChatMessage message={message} onSelect={handleSelect} />);

      const messageElement = screen.getByText(message.content).closest('.chat-message');
      fireEvent.click(messageElement!);

      // User messages don't have onClick handler
      expect(handleSelect).not.toHaveBeenCalled();
    });
  });

  describe('Source toggle isolation', () => {
    it('stops event propagation when clicking source toggle', () => {
      const message = createMockAssistantMessage();
      const handleSelect = vi.fn();

      render(<ChatMessage message={message} onSelect={handleSelect} />);

      const toggleButton = screen.getByText(/\d+ source/);
      fireEvent.click(toggleButton);

      // onSelect should not be called when clicking the sources button
      expect(handleSelect).not.toHaveBeenCalled();
    });
  });
});
