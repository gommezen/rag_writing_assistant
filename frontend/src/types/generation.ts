/**
 * Generation-related types.
 */

import type { ConfidenceLevel, RetrievalMetadata, SourceReference } from './common';

export interface GeneratedSection {
  section_id: string;
  content: string;
  sources: SourceReference[]; // Never null, empty array if no sources
  confidence: ConfidenceLevel;
  warnings: string[];
  is_user_edited: boolean;
}

export interface GenerationRequest {
  prompt: string;
  document_ids?: string[];
  max_sections?: number;
}

export interface GenerationResponse {
  generation_id: string;
  sections: GeneratedSection[];
  retrieval_metadata: RetrievalMetadata;
  total_sources_used: number;
  generation_time_ms: number;
  model_used: string;
  created_at: string;
}

export interface RegenerateSectionRequest {
  section_id: string;
  original_content: string;
  refinement_prompt?: string;
  document_ids?: string[];
}

export interface RegenerateSectionResponse {
  section: GeneratedSection;
  retrieval_metadata: RetrievalMetadata;
  generation_time_ms: number;
}

/**
 * Local state for edited sections.
 * Extends GeneratedSection with edit tracking.
 */
export interface EditableSection extends GeneratedSection {
  original_content: string;
  has_unsaved_changes: boolean;
}
