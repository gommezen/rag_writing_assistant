/**
 * Tests for ChatInput component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatInput } from './ChatInput';

describe('ChatInput', () => {
  describe('Basic rendering', () => {
    it('renders textarea with default placeholder', () => {
      const handleSend = vi.fn();

      render(<ChatInput onSend={handleSend} />);

      const textarea = screen.getByPlaceholderText('Ask a question about your documents...');
      expect(textarea).toBeInTheDocument();
    });

    it('renders textarea with custom placeholder', () => {
      const handleSend = vi.fn();

      render(<ChatInput onSend={handleSend} placeholder="Custom placeholder" />);

      const textarea = screen.getByPlaceholderText('Custom placeholder');
      expect(textarea).toBeInTheDocument();
    });

    it('renders send button', () => {
      const handleSend = vi.fn();

      render(<ChatInput onSend={handleSend} />);

      const sendButton = screen.getByTitle('Send message (Enter)');
      expect(sendButton).toBeInTheDocument();
    });
  });

  describe('Message sending', () => {
    it('calls onSend with trimmed message on button click', async () => {
      const handleSend = vi.fn();
      const user = userEvent.setup();

      render(<ChatInput onSend={handleSend} />);

      const textarea = screen.getByRole('textbox');
      const sendButton = screen.getByTitle('Send message (Enter)');

      await user.type(textarea, '  Test message  ');
      await user.click(sendButton);

      expect(handleSend).toHaveBeenCalledWith('Test message');
    });

    it('calls onSend on Enter key press', async () => {
      const handleSend = vi.fn();
      const user = userEvent.setup();

      render(<ChatInput onSend={handleSend} />);

      const textarea = screen.getByRole('textbox');

      await user.type(textarea, 'Test message{Enter}');

      expect(handleSend).toHaveBeenCalledWith('Test message');
    });

    it('does not call onSend on Shift+Enter', async () => {
      const handleSend = vi.fn();
      const user = userEvent.setup();

      render(<ChatInput onSend={handleSend} />);

      const textarea = screen.getByRole('textbox');

      await user.type(textarea, 'Line 1{Shift>}{Enter}{/Shift}Line 2');

      expect(handleSend).not.toHaveBeenCalled();
      expect(textarea).toHaveValue('Line 1\nLine 2');
    });

    it('clears textarea after sending', async () => {
      const handleSend = vi.fn();
      const user = userEvent.setup();

      render(<ChatInput onSend={handleSend} />);

      const textarea = screen.getByRole('textbox');
      const sendButton = screen.getByTitle('Send message (Enter)');

      await user.type(textarea, 'Test message');
      await user.click(sendButton);

      expect(textarea).toHaveValue('');
    });

    it('does not call onSend for empty messages', async () => {
      const handleSend = vi.fn();
      const user = userEvent.setup();

      render(<ChatInput onSend={handleSend} />);

      const textarea = screen.getByRole('textbox');

      await user.type(textarea, '   ');
      await user.keyboard('{Enter}');

      expect(handleSend).not.toHaveBeenCalled();
    });

    it('does not call onSend for whitespace-only messages', async () => {
      const handleSend = vi.fn();
      const user = userEvent.setup();

      render(<ChatInput onSend={handleSend} />);

      const textarea = screen.getByRole('textbox');
      const sendButton = screen.getByTitle('Send message (Enter)');

      await user.type(textarea, '   \n\t  ');
      await user.click(sendButton);

      expect(handleSend).not.toHaveBeenCalled();
    });
  });

  describe('Disabled state', () => {
    it('disables textarea when disabled prop is true', () => {
      const handleSend = vi.fn();

      render(<ChatInput onSend={handleSend} disabled={true} />);

      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeDisabled();
    });

    it('disables send button when disabled prop is true', () => {
      const handleSend = vi.fn();

      render(<ChatInput onSend={handleSend} disabled={true} />);

      const sendButton = screen.getByTitle('Send message (Enter)');
      expect(sendButton).toBeDisabled();
    });

    it('does not call onSend when disabled', async () => {
      const handleSend = vi.fn();
      const user = userEvent.setup();

      render(<ChatInput onSend={handleSend} disabled={true} />);

      const textarea = screen.getByRole('textbox');

      // Try to type (will fail since disabled, but let's verify behavior)
      await user.click(textarea);

      expect(handleSend).not.toHaveBeenCalled();
    });

    it('disables send button when message is empty', async () => {
      const handleSend = vi.fn();

      render(<ChatInput onSend={handleSend} />);

      const sendButton = screen.getByTitle('Send message (Enter)');
      expect(sendButton).toBeDisabled();
    });

    it('enables send button when message has content', async () => {
      const handleSend = vi.fn();
      const user = userEvent.setup();

      render(<ChatInput onSend={handleSend} />);

      const textarea = screen.getByRole('textbox');
      const sendButton = screen.getByTitle('Send message (Enter)');

      await user.type(textarea, 'Test');

      expect(sendButton).not.toBeDisabled();
    });
  });

  describe('Input handling', () => {
    it('updates textarea value on typing', async () => {
      const handleSend = vi.fn();
      const user = userEvent.setup();

      render(<ChatInput onSend={handleSend} />);

      const textarea = screen.getByRole('textbox');

      await user.type(textarea, 'Hello world');

      expect(textarea).toHaveValue('Hello world');
    });

    it('maintains multiline content with Shift+Enter', async () => {
      const handleSend = vi.fn();
      const user = userEvent.setup();

      render(<ChatInput onSend={handleSend} />);

      const textarea = screen.getByRole('textbox');

      await user.type(textarea, 'First line');
      await user.keyboard('{Shift>}{Enter}{/Shift}');
      await user.type(textarea, 'Second line');

      expect(textarea).toHaveValue('First line\nSecond line');
    });
  });
});
