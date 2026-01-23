/**
 * Document-related types.
 */

export type DocumentType = 'pdf' | 'docx' | 'txt';

export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed';

export interface DocumentMetadata {
  title: string;
  author: string | null;
  created_date: string | null;
  source_path: string | null;
  page_count: number | null;
  word_count: number | null;
  custom_metadata: Record<string, string>;
}

export interface Document {
  document_id: string;
  filename: string;
  document_type: DocumentType;
  status: DocumentStatus;
  metadata: DocumentMetadata;
  chunk_count: number;
  created_at: string;
  updated_at: string;
  error_message: string | null;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
}

export interface UploadDocumentParams {
  file: File;
  title?: string;
  author?: string;
}

export interface ChunkResponse {
  chunk_id: string;
  chunk_index: number;
  content: string;
  page_number: number | null;
  section_title: string | null;
}

export interface DocumentChunksResponse {
  document_id: string;
  chunks: ChunkResponse[];
  total_chunks: number;
}
