/**
 * Common types used across the application.
 * These types match the backend data models to ensure type safety.
 */

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'unknown';

export type QueryIntent = 'analysis' | 'qa' | 'writing';

export type RetrievalType = 'similarity' | 'diverse';

export type SummaryScope = 'broad' | 'focused' | 'not_applicable';

export interface SourceReference {
  document_id: string;
  chunk_id: string;
  excerpt: string;
  relevance_score: number;
  metadata: Record<string, string>;
}

export interface DocumentCoverage {
  document_id: string;
  document_title: string;
  chunks_seen: number;
  chunks_total: number;
  coverage_percentage: number;
  regions_covered: string[];
  regions_missing: string[];
}

export interface CoverageDescriptor {
  retrieval_type: string;
  chunks_seen: number;
  chunks_total: number;
  coverage_percentage: number;
  document_coverage: Record<string, DocumentCoverage>;
  blind_spots: string[];
  coverage_summary: string;
}

export interface IntentClassification {
  intent: QueryIntent;
  confidence: number;
  reasoning: string;
  suggested_retrieval: RetrievalType;
  summary_scope: SummaryScope;
  focus_topic: string | null;
}

export interface RetrievalMetadata {
  query: string;
  top_k: number;
  similarity_threshold: number;
  chunks_retrieved: number;
  chunks_above_threshold: number;
  retrieval_time_ms: number;
  timestamp: string;
  retrieval_type?: string;
  coverage?: CoverageDescriptor;
  intent?: IntentClassification;
}

export interface ApiError {
  error: string;
  details?: Record<string, unknown>;
}
