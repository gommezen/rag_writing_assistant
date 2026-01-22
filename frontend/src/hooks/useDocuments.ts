/**
 * React Query hooks for document operations.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { UploadDocumentParams } from '../types';

const DOCUMENTS_KEY = ['documents'];

export function useDocuments() {
  return useQuery({
    queryKey: DOCUMENTS_KEY,
    queryFn: () => apiClient.listDocuments(),
  });
}

export function useDocument(documentId: string) {
  return useQuery({
    queryKey: [...DOCUMENTS_KEY, documentId],
    queryFn: () => apiClient.getDocument(documentId),
    enabled: !!documentId,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: UploadDocumentParams) => apiClient.uploadDocument(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY });
    },
  });
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
