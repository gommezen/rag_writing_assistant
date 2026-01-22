/**
 * Tests for useGeneration hooks.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useGenerateDraft, useRegenerateSection } from './useGeneration';
import {
  createMockGenerationResponse,
  createMockSection,
  createMockRetrievalMetadata,
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

describe('useGenerateDraft', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls API correctly on mutate', async () => {
    const mockResponse = createMockGenerationResponse();
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockFetchResponse(mockResponse)
    );

    const { result } = renderHook(() => useGenerateDraft(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ prompt: 'Test prompt' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalledWith('/api/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt: 'Test prompt' }),
    });
  });

  it('returns generation response on success', async () => {
    const mockResponse = createMockGenerationResponse({
      generation_id: 'test-gen-id',
    });
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockFetchResponse(mockResponse)
    );

    const { result } = renderHook(() => useGenerateDraft(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ prompt: 'Test prompt' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.generation_id).toBe('test-gen-id');
  });

  it('handles errors', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ error: 'Server error' }),
    } as Response);

    const { result } = renderHook(() => useGenerateDraft(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ prompt: 'Test prompt' });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });

  it('provides loading state', async () => {
    const mockResponse = createMockGenerationResponse();
    let resolvePromise: (value: Response) => void;
    const promise = new Promise<Response>((resolve) => {
      resolvePromise = resolve;
    });

    (global.fetch as ReturnType<typeof vi.fn>).mockReturnValueOnce(promise);

    const { result } = renderHook(() => useGenerateDraft(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ prompt: 'Test prompt' });

    await waitFor(() => {
      expect(result.current.isPending).toBe(true);
    });

    resolvePromise!(createMockFetchResponse(mockResponse));

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe('useRegenerateSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls API correctly on mutate', async () => {
    const mockResponse = {
      section: createMockSection(),
      retrieval_metadata: createMockRetrievalMetadata(),
      generation_time_ms: 500,
    };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockFetchResponse(mockResponse)
    );

    const { result } = renderHook(() => useRegenerateSection(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      section_id: 'sec-1',
      prompt: 'Improve this section',
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalledWith('/api/generate/section', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        section_id: 'sec-1',
        prompt: 'Improve this section',
      }),
    });
  });

  it('returns regenerated section on success', async () => {
    const section = createMockSection({ section_id: 'sec-regen' });
    const mockResponse = {
      section,
      retrieval_metadata: createMockRetrievalMetadata(),
      generation_time_ms: 500,
    };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      createMockFetchResponse(mockResponse)
    );

    const { result } = renderHook(() => useRegenerateSection(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ section_id: 'sec-1' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.section.section_id).toBe('sec-regen');
  });
});
