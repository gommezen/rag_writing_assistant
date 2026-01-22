/**
 * Common types used across the application.
 * These types match the backend data models to ensure type safety.
 */

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'unknown';

export interface SourceReference {
  document_id: string;
  chunk_id: string;
  excerpt: string;
  relevance_score: number;
  metadata: Record<string, string>;
}

export interface RetrievalMetadata {
  query: string;
  top_k: number;
  similarity_threshold: number;
  chunks_retrieved: number;
  chunks_above_threshold: number;
  retrieval_time_ms: number;
  timestamp: string;
}

export interface ApiError {
  error: string;
  details?: Record<string, unknown>;
}
