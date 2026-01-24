/**
 * React Query hooks for chat operations.
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { ChatRequest } from '../types';

export function useChat() {
  return useMutation({
    mutationFn: (request: ChatRequest) => apiClient.chat(request),
  });
}

export function useConversation(conversationId: string | null) {
  return useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => apiClient.getConversation(conversationId!),
    enabled: !!conversationId,
  });
}
