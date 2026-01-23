/**
 * DocumentPreview component - Modal to preview document chunks.
 */

import { X } from 'lucide-react';
import type { ChunkResponse } from '../../types';
import './DocumentPreview.css';

interface DocumentPreviewProps {
  documentTitle: string;
  chunks: ChunkResponse[];
  isLoading: boolean;
  onClose: () => void;
}

export function DocumentPreview({
  documentTitle,
  chunks,
  isLoading,
  onClose,
}: DocumentPreviewProps) {
  // Close on escape key
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  // Close on backdrop click
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="document-preview-overlay"
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-labelledby="preview-title"
    >
      <div className="document-preview">
        <header className="document-preview__header">
          <h2 id="preview-title" className="document-preview__title">
            {documentTitle}
          </h2>
          <button
            type="button"
            className="document-preview__close"
            onClick={onClose}
            aria-label="Close preview"
          >
            <X size={20} />
          </button>
        </header>

        <div className="document-preview__content">
          {isLoading ? (
            <div className="document-preview__loading">
              Loading document content...
            </div>
          ) : chunks.length === 0 ? (
            <div className="document-preview__empty">
              No content available for this document.
            </div>
          ) : (
            <div className="document-preview__chunks">
              {chunks.map((chunk) => (
                <article key={chunk.chunk_id} className="preview-chunk">
                  <header className="preview-chunk__header">
                    <span className="preview-chunk__index">
                      Chunk {chunk.chunk_index + 1}
                    </span>
                    {chunk.page_number && (
                      <span className="preview-chunk__page">
                        Page {chunk.page_number}
                      </span>
                    )}
                    {chunk.section_title && (
                      <span className="preview-chunk__section">
                        {chunk.section_title}
                      </span>
                    )}
                  </header>
                  <p className="preview-chunk__content">{chunk.content}</p>
                </article>
              ))}
            </div>
          )}
        </div>

        <footer className="document-preview__footer">
          <span className="document-preview__count">
            {chunks.length} chunk{chunks.length !== 1 ? 's' : ''} indexed
          </span>
        </footer>
      </div>
    </div>
  );
}
