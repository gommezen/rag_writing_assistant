/**
 * API client for the RAG Document Intelligence backend.
 */

import type {
  ApiError,
  ChatRequest,
  ChatResponse,
  Conversation,
  ConversationSummary,
  Document,
  DocumentChunksResponse,
  DocumentListResponse,
  GenerationRequest,
  GenerationResponse,
  RegenerateSectionRequest,
  RegenerateSectionResponse,
  SuggestedQuestionsRequest,
  SuggestedQuestionsResponse,
  UploadDocumentParams,
  UploadFromUrlParams,
} from '../types';

const API_BASE = '/api';

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
      },
    });

    if (!response.ok) {
      let error: ApiError;
      try {
        error = await response.json();
      } catch {
        error = { error: `Request failed with status ${response.status}` };
      }
      throw new Error(error.error);
    }

    return response.json();
  }

  // Health check
  async healthCheck(): Promise<{ status: string; vector_store: Record<string, unknown> }> {
    return this.request('/health');
  }

  // Document operations
  async uploadDocument(params: UploadDocumentParams): Promise<Document> {
    const formData = new FormData();
    formData.append('file', params.file);
    if (params.title) {
      formData.append('title', params.title);
    }
    if (params.author) {
      formData.append('author', params.author);
    }

    return this.request('/documents', {
      method: 'POST',
      body: formData,
    });
  }

  async listDocuments(): Promise<DocumentListResponse> {
    return this.request('/documents');
  }

  async getDocument(documentId: string): Promise<Document> {
    return this.request(`/documents/${documentId}`);
  }

  async deleteDocument(documentId: string): Promise<{ status: string; document_id: string }> {
    return this.request(`/documents/${documentId}`, {
      method: 'DELETE',
    });
  }

  async retryDocument(documentId: string): Promise<Document> {
    return this.request(`/documents/${documentId}/retry`, {
      method: 'POST',
    });
  }

  async uploadFromUrl(params: UploadFromUrlParams): Promise<Document> {
    return this.request('/documents/from-url', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });
  }

  async getDocumentChunks(documentId: string): Promise<DocumentChunksResponse> {
    return this.request(`/documents/${documentId}/chunks`);
  }

  // Generation operations
  async generateDraft(request: GenerationRequest): Promise<GenerationResponse> {
    return this.request('/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
  }

  async regenerateSection(
    request: RegenerateSectionRequest
  ): Promise<RegenerateSectionResponse> {
    return this.request('/generate/section', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
  }

  async generateSuggestions(
    request: SuggestedQuestionsRequest = {}
  ): Promise<SuggestedQuestionsResponse> {
    return this.request('/generate/suggestions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
  }

  // Chat operations
  async chat(request: ChatRequest): Promise<ChatResponse> {
    return this.request('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
  }

  async getConversation(conversationId: string): Promise<Conversation> {
    return this.request(`/chat/${conversationId}`);
  }

  async listConversations(): Promise<ConversationSummary[]> {
    return this.request('/chat');
  }

  async deleteConversation(conversationId: string): Promise<{ message: string }> {
    return this.request(`/chat/${conversationId}`, {
      method: 'DELETE',
    });
  }

  async updateConversationTitle(
    conversationId: string,
    title: string
  ): Promise<{ message: string }> {
    return this.request(`/chat/${conversationId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title }),
    });
  }

  // Export operations
  async exportDocument(
    sections: { heading: string; content: string; sources: { document_title: string; chunk_index?: number; relevance_score?: number }[] }[],
    format: 'docx' | 'pdf',
    documentTitle: string
  ): Promise<Blob> {
    const url = `${API_BASE}/export`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sections,
        format,
        document_title: documentTitle,
      }),
    });
    if (!response.ok) {
      throw new Error(`Export failed with status ${response.status}`);
    }
    return response.blob();
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
