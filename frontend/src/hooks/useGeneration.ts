/**
 * React Query hooks for generation operations.
 */

import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { GenerationRequest, RegenerateSectionRequest, SuggestedQuestionsRequest } from '../types';

export function useGenerateDraft() {
  return useMutation({
    mutationFn: (request: GenerationRequest) => apiClient.generateDraft(request),
  });
}

export function useRegenerateSection() {
  return useMutation({
    mutationFn: (request: RegenerateSectionRequest) =>
      apiClient.regenerateSection(request),
  });
}

export function useSuggestedQuestions() {
  return useMutation({
    mutationFn: (request: SuggestedQuestionsRequest = {}) =>
      apiClient.generateSuggestions(request),
  });
}
