/**
 * React Query hooks for document operations.
 */

import { useEffect, useState, useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { UploadDocumentParams, Document } from '../types';

const DOCUMENTS_KEY = ['documents'];

export function useDocuments() {
  return useQuery({
    queryKey: DOCUMENTS_KEY,
    queryFn: () => apiClient.listDocuments(),
    retry: true,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
  });
}

export function useDocument(documentId: string) {
  return useQuery({
    queryKey: [...DOCUMENTS_KEY, documentId],
    queryFn: () => apiClient.getDocument(documentId),
    enabled: !!documentId,
  });
}

/**
 * Hook to poll a document's status until it's ready or failed.
 * Automatically stops polling when document reaches a terminal state.
 */
export function useDocumentPolling(documentId: string | null) {
  const queryClient = useQueryClient();
  const [pollCount, setPollCount] = useState(0);
  const maxPolls = 60; // Stop after ~2 minutes (60 * 2 seconds)

  const query = useQuery({
    queryKey: [...DOCUMENTS_KEY, documentId, 'poll'],
    queryFn: () => apiClient.getDocument(documentId!),
    enabled: !!documentId && pollCount < maxPolls,
    refetchInterval: (query) => {
      const doc = query.state.data;
      // Stop polling if document is in terminal state
      if (doc?.status === 'ready' || doc?.status === 'failed') {
        // Invalidate the documents list to refresh UI
        queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY });
        return false;
      }
      // Continue polling every 2 seconds
      return 2000;
    },
  });

  // Track poll count to implement timeout
  useEffect(() => {
    if (query.dataUpdatedAt && documentId) {
      setPollCount((prev) => prev + 1);
    }
  }, [query.dataUpdatedAt, documentId]);

  // Reset poll count when document ID changes
  useEffect(() => {
    setPollCount(0);
  }, [documentId]);

  return {
    ...query,
    isTimedOut: pollCount >= maxPolls && query.data?.status !== 'ready' && query.data?.status !== 'failed',
  };
}

/**
 * Upload a document and track processing status.
 * Returns the uploaded document ID for polling.
 */
export function useUploadDocument() {
  const queryClient = useQueryClient();
  const [uploadedDocumentId, setUploadedDocumentId] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (params: UploadDocumentParams) => apiClient.uploadDocument(params),
    onSuccess: (document: Document) => {
      // Invalidate documents list immediately to show the new document
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY });
      // Track the document ID for polling if not ready yet
      if (document.status !== 'ready') {
        setUploadedDocumentId(document.document_id);
      }
    },
  });

  // Clear the uploaded document ID when polling completes
  const clearUploadedDocumentId = useCallback(() => {
    setUploadedDocumentId(null);
  }, []);

  return {
    ...mutation,
    uploadedDocumentId,
    clearUploadedDocumentId,
  };
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) => apiClient.deleteDocument(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY });
    },
  });
}

export function useDocumentChunks(documentId: string | null) {
  return useQuery({
    queryKey: [...DOCUMENTS_KEY, documentId, 'chunks'],
    queryFn: () => apiClient.getDocumentChunks(documentId!),
    enabled: !!documentId,
  });
}
