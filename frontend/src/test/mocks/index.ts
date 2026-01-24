/**
 * Mock factories for testing.
 *
 * These factories create consistent mock data that matches
 * the application's type system.
 */

import type {
  SourceReference,
  GeneratedSection,
  GenerationResponse,
  RetrievalMetadata,
  Document,
  ConfidenceLevel,
} from '../../types';

/**
 * Create a mock source reference with optional overrides.
 */
export function createMockSource(
  overrides: Partial<SourceReference> = {}
): SourceReference {
  return {
    document_id: 'doc-001',
    chunk_id: `chunk-${Math.random().toString(36).substr(2, 9)}`,
    excerpt: 'This is a sample excerpt from the source document for testing purposes.',
    relevance_score: 0.85,
    metadata: {
      title: 'Test Document',
      filename: 'test.pdf',
    },
    ...overrides,
  };
}

/**
 * Create multiple mock sources.
 */
export function createMockSources(
  count: number = 3,
  baseOverrides: Partial<SourceReference> = {}
): SourceReference[] {
  return Array.from({ length: count }, (_, i) =>
    createMockSource({
      chunk_id: `chunk-${i + 1}`,
      relevance_score: 0.9 - i * 0.1,
      excerpt: `Source excerpt ${i + 1} with relevant content.`,
      ...baseOverrides,
    })
  );
}

/**
 * Create a mock generated section with optional overrides.
 */
export function createMockSection(
  overrides: Partial<GeneratedSection> = {}
): GeneratedSection {
  return {
    section_id: `section-${Math.random().toString(36).substr(2, 9)}`,
    content: 'This is generated content for testing. [Source 1] It includes citations.',
    sources: createMockSources(2),
    confidence: 'high' as ConfidenceLevel,
    warnings: [],
    is_user_edited: false,
    ...overrides,
  };
}

/**
 * Create multiple mock sections.
 */
export function createMockSections(
  count: number = 3,
  baseOverrides: Partial<GeneratedSection> = {}
): GeneratedSection[] {
  return Array.from({ length: count }, (_, i) =>
    createMockSection({
      section_id: `section-${i + 1}`,
      content: `Section ${i + 1} content with [Source 1] citations.`,
      ...baseOverrides,
    })
  );
}

/**
 * Create mock retrieval metadata.
 */
export function createMockRetrievalMetadata(
  overrides: Partial<RetrievalMetadata> = {}
): RetrievalMetadata {
  return {
    query: 'test query',
    top_k: 10,
    similarity_threshold: 0.7,
    chunks_retrieved: 5,
    chunks_above_threshold: 3,
    retrieval_time_ms: 15.5,
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

/**
 * Create a mock generation response.
 */
export function createMockGenerationResponse(
  overrides: Partial<GenerationResponse> = {}
): GenerationResponse {
  return {
    generation_id: `gen-${Math.random().toString(36).substr(2, 9)}`,
    sections: createMockSections(2),
    retrieval_metadata: createMockRetrievalMetadata(),
    total_sources_used: 5,
    generation_time_ms: 1250.5,
    model_used: 'llama3.2',
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

/**
 * Create a mock document.
 */
export function createMockDocument(overrides: Partial<Document> = {}): Document {
  return {
    document_id: `doc-${Math.random().toString(36).substr(2, 9)}`,
    filename: 'test_document.pdf',
    document_type: 'pdf',
    status: 'ready',
    metadata: {
      title: 'Test Document',
      author: null,
      created_date: null,
      source_path: 'test_document.pdf',
      page_count: 10,
      word_count: 1500,
      custom_metadata: {},
    },
    chunk_count: 15,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    error_message: null,
    ...overrides,
  };
}

/**
 * Create mock fetch response helper.
 */
export function createMockFetchResponse<T>(data: T, ok: boolean = true): Response {
  return {
    ok,
    status: ok ? 200 : 500,
    json: async () => data,
    text: async () => JSON.stringify(data),
    headers: new Headers({ 'Content-Type': 'application/json' }),
  } as Response;
}

/**
 * Create mock error response.
 */
export function createMockErrorResponse(
  message: string,
  status: number = 500
): Response {
  return {
    ok: false,
    status,
    json: async () => ({ error: message }),
    text: async () => JSON.stringify({ error: message }),
    headers: new Headers({ 'Content-Type': 'application/json' }),
  } as Response;
}

// ============================================================================
// Chat Mocks
// ============================================================================

import type {
  ChatMessage,
  ChatResponse,
  ContextUsed,
  Conversation,
} from '../../types';

/**
 * Create a mock chat message.
 */
export function createMockChatMessage(
  overrides: Partial<ChatMessage> = {}
): ChatMessage {
  return {
    message_id: `msg-${Math.random().toString(36).substr(2, 9)}`,
    role: 'user',
    content: 'This is a test message.',
    timestamp: new Date().toISOString(),
    sources_used: [],
    ...overrides,
  };
}

/**
 * Create a mock assistant chat message with sources.
 */
export function createMockAssistantMessage(
  overrides: Partial<ChatMessage> = {}
): ChatMessage {
  return createMockChatMessage({
    role: 'assistant',
    content: 'Based on [Source 1], here is the response with citations.',
    sources_used: createMockSources(2),
    ...overrides,
  });
}

/**
 * Create mock context used info.
 */
export function createMockContextUsed(
  overrides: Partial<ContextUsed> = {}
): ContextUsed {
  return {
    history_messages_count: 4,
    history_truncated: false,
    sources_count: 3,
    ...overrides,
  };
}

/**
 * Create a mock chat response.
 */
export function createMockChatResponse(
  overrides: Partial<ChatResponse> = {}
): ChatResponse {
  return {
    conversation_id: `conv-${Math.random().toString(36).substr(2, 9)}`,
    message: createMockAssistantMessage(),
    cumulative_coverage: null,
    context_used: createMockContextUsed(),
    generation_time_ms: 850.5,
    model_used: 'llama3.2',
    ...overrides,
  };
}

/**
 * Create a mock conversation.
 */
export function createMockConversation(
  overrides: Partial<Conversation> = {}
): Conversation {
  return {
    conversation_id: `conv-${Math.random().toString(36).substr(2, 9)}`,
    messages: [
      createMockChatMessage({ role: 'user', content: 'What is this document about?' }),
      createMockAssistantMessage({ content: 'This document discusses testing methodologies.' }),
    ],
    document_ids: null,
    cumulative_coverage: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}
