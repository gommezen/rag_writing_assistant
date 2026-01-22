/**
 * Tests for API client.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from './client';
import {
  createMockGenerationResponse,
  createMockDocument,
  createMockFetchResponse,
  createMockErrorResponse,
  createMockSection,
  createMockRetrievalMetadata,
} from '../test/mocks';

describe('apiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('generateDraft', () => {
    it('sends correct request with prompt', async () => {
      const mockResponse = createMockGenerationResponse();
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockFetchResponse(mockResponse)
      );

      await apiClient.generateDraft({ prompt: 'Write about testing' });

      expect(global.fetch).toHaveBeenCalledWith('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: 'Write about testing' }),
      });
    });

    it('sends request with optional document_ids', async () => {
      const mockResponse = createMockGenerationResponse();
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockFetchResponse(mockResponse)
      );

      await apiClient.generateDraft({
        prompt: 'Test',
        document_ids: ['doc-1', 'doc-2'],
      });

      expect(global.fetch).toHaveBeenCalledWith('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: 'Test',
          document_ids: ['doc-1', 'doc-2'],
        }),
      });
    });

    it('returns generation response', async () => {
      const mockResponse = createMockGenerationResponse({
        generation_id: 'gen-test-123',
      });
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockFetchResponse(mockResponse)
      );

      const result = await apiClient.generateDraft({ prompt: 'Test' });

      expect(result.generation_id).toBe('gen-test-123');
      expect(result.sections).toBeDefined();
      expect(result.retrieval_metadata).toBeDefined();
    });

    it('handles 503 LLM error', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockErrorResponse('LLM service unavailable', 503)
      );

      await expect(apiClient.generateDraft({ prompt: 'Test' })).rejects.toThrow(
        'LLM service unavailable'
      );
    });
  });

  describe('regenerateSection', () => {
    it('sends correct request', async () => {
      const mockResponse = {
        section: createMockSection(),
        retrieval_metadata: createMockRetrievalMetadata(),
        generation_time_ms: 500,
      };
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockFetchResponse(mockResponse)
      );

      await apiClient.regenerateSection({
        section_id: 'sec-1',
        prompt: 'Make it better',
      });

      expect(global.fetch).toHaveBeenCalledWith('/api/generate/section', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          section_id: 'sec-1',
          prompt: 'Make it better',
        }),
      });
    });
  });

  describe('uploadDocument', () => {
    it('sends FormData with file', async () => {
      const mockDoc = createMockDocument();
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockFetchResponse(mockDoc)
      );

      const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
      await apiClient.uploadDocument({ file });

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/documents',
        expect.objectContaining({
          method: 'POST',
        })
      );
      // Verify FormData was sent
      const fetchCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(fetchCall[1].body).toBeInstanceOf(FormData);
    });

    it('includes title and author in FormData when provided', async () => {
      const mockDoc = createMockDocument();
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockFetchResponse(mockDoc)
      );

      const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
      await apiClient.uploadDocument({
        file,
        title: 'My Document',
        author: 'Test Author',
      });

      const fetchCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      const formData = fetchCall[1].body as FormData;

      expect(formData.get('file')).toBeInstanceOf(File);
      expect(formData.get('title')).toBe('My Document');
      expect(formData.get('author')).toBe('Test Author');
    });
  });

  describe('listDocuments', () => {
    it('sends GET request to documents endpoint', async () => {
      const mockResponse = {
        documents: [createMockDocument()],
        total: 1,
      };
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockFetchResponse(mockResponse)
      );

      await apiClient.listDocuments();

      expect(global.fetch).toHaveBeenCalledWith('/api/documents', expect.any(Object));
    });

    it('returns document list', async () => {
      const mockResponse = {
        documents: [createMockDocument(), createMockDocument()],
        total: 2,
      };
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockFetchResponse(mockResponse)
      );

      const result = await apiClient.listDocuments();

      expect(result.total).toBe(2);
      expect(result.documents).toHaveLength(2);
    });
  });

  describe('getDocument', () => {
    it('sends GET request with document ID', async () => {
      const mockDoc = createMockDocument({ document_id: 'doc-123' });
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockFetchResponse(mockDoc)
      );

      await apiClient.getDocument('doc-123');

      expect(global.fetch).toHaveBeenCalledWith('/api/documents/doc-123', expect.any(Object));
    });
  });

  describe('deleteDocument', () => {
    it('sends DELETE request with document ID', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockFetchResponse({ status: 'deleted', document_id: 'doc-123' })
      );

      await apiClient.deleteDocument('doc-123');

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/documents/doc-123',
        expect.objectContaining({ method: 'DELETE' })
      );
    });
  });

  describe('healthCheck', () => {
    it('sends GET request to health endpoint', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockFetchResponse({
          status: 'healthy',
          vector_store: { total_chunks: 100 },
        })
      );

      await apiClient.healthCheck();

      expect(global.fetch).toHaveBeenCalledWith('/api/health', expect.any(Object));
    });
  });

  describe('error handling', () => {
    it('handles network errors', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Network error')
      );

      await expect(apiClient.generateDraft({ prompt: 'Test' })).rejects.toThrow(
        'Network error'
      );
    });

    it('handles non-JSON error responses', async () => {
      const errorResponse = {
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      } as Response;

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(errorResponse);

      await expect(apiClient.generateDraft({ prompt: 'Test' })).rejects.toThrow(
        'Request failed with status 500'
      );
    });

    it('extracts error message from JSON response', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
        createMockErrorResponse('Custom error message', 400)
      );

      await expect(apiClient.generateDraft({ prompt: 'Test' })).rejects.toThrow(
        'Custom error message'
      );
    });
  });
});
