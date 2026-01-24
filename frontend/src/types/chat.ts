/**
 * Chat-related types for multi-turn conversations.
 */

import type { CoverageDescriptor, SourceReference } from './common';
import type { GeneratedSection } from './generation';

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  message_id: string;
  role: ChatRole;
  content: string;
  timestamp: string;
  sections?: GeneratedSection[];
  sources_used: SourceReference[];
}

export interface ContextUsed {
  history_messages_count: number;
  history_truncated: boolean;
  sources_count: number;
}

export interface Conversation {
  conversation_id: string;
  messages: ChatMessage[];
  document_ids: string[] | null;
  cumulative_coverage: CoverageDescriptor | null;
  created_at: string;
  updated_at: string;
}

export interface ChatRequest {
  conversation_id?: string;
  message: string;
  document_ids?: string[];
  include_history?: boolean;
  history_turns?: number;
}

export interface ChatResponse {
  conversation_id: string;
  message: ChatMessage;
  cumulative_coverage: CoverageDescriptor | null;
  context_used: ContextUsed;
  generation_time_ms: number;
  model_used: string;
}
