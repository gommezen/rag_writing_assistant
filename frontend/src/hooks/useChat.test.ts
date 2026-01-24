/**
 * Tests for useChat and useConversation hooks.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useChat, useConversation } from './useChat';
import {
  createMockChatResponse,
  createMockConversation,
  createMockFetchResponse,
} from '../test/mocks';
import React from 'react';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    );
  };
}

describe('useChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls API correctly for new conversation', async () => {
    const mockResponse = createMockChatResponse();
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockFetchResponse(mockResponse)
    );

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ message: 'Test message' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalledWith('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: 'Test message' }),
    });
  });

  it('calls API correctly for continuing conversation', async () => {
    const mockResponse = createMockChatResponse({ conversation_id: 'conv-123' });
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockFetchResponse(mockResponse)
    );

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      conversation_id: 'conv-123',
      message: 'Follow-up message',
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalledWith('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        conversation_id: 'conv-123',
        message: 'Follow-up message',
      }),
    });
  });

  it('returns chat response on success', async () => {
    const mockResponse = createMockChatResponse({
      conversation_id: 'conv-test',
    });
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockFetchResponse(mockResponse)
    );

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ message: 'Test message' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.conversation_id).toBe('conv-test');
    expect(result.current.data?.message).toBeDefined();
    expect(result.current.data?.context_used).toBeDefined();
  });

  it('handles errors', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ error: 'Server error' }),
    } as Response);

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ message: 'Test message' });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });

  it('provides loading state', async () => {
    const mockResponse = createMockChatResponse();
    let resolvePromise: (value: Response) => void;
    const promise = new Promise<Response>((resolve) => {
      resolvePromise = resolve;
    });

    (global.fetch as ReturnType<typeof vi.fn>).mockReturnValueOnce(promise);

    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ message: 'Test message' });

    await waitFor(() => {
      expect(result.current.isPending).toBe(true);
    });

    resolvePromise!(createMockFetchResponse(mockResponse));

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe('useConversation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches conversation by ID', async () => {
    const mockConversation = createMockConversation({ conversation_id: 'conv-abc' });
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockFetchResponse(mockConversation)
    );

    const { result } = renderHook(() => useConversation('conv-abc'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Verify fetch was called with correct URL
    expect(global.fetch).toHaveBeenCalledWith('/api/chat/conv-abc', expect.objectContaining({
      headers: expect.any(Object),
    }));
    expect(result.current.data?.conversation_id).toBe('conv-abc');
  });

  it('does not fetch when conversationId is null', () => {
    const { result } = renderHook(() => useConversation(null), {
      wrapper: createWrapper(),
    });

    // Query should be disabled and not fetch
    expect(result.current.fetchStatus).toBe('idle');
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
