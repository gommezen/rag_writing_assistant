/**
 * React Query hooks for generation operations.
 */

import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { GenerationRequest, RegenerateSectionRequest } from '../types';

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
