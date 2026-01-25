/**
 * React Query hooks for chat operations.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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

export function useConversations() {
  return useQuery({
    queryKey: ['conversations'],
    queryFn: () => apiClient.listConversations(),
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) => apiClient.deleteConversation(conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}

export function useUpdateConversationTitle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, title }: { conversationId: string; title: string }) =>
      apiClient.updateConversationTitle(conversationId, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}
