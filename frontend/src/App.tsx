/**
 * Main App component for the RAG Writing Assistant.
 *
 * Layout: Three-panel design
 * - Left sidebar: Document management
 * - Center: Document editor
 * - Right sidebar: Source details (part of DocumentEditor)
 */

import { useState, useCallback } from 'react';
import { DocumentEditor } from './components/DocumentEditor';
import { WarningBanner } from './components/WarningBanner';
import {
  useDocuments,
  useUploadDocument,
  useDeleteDocument,
  useGenerateDraft,
  useRegenerateSection,
} from './hooks';
import type { GeneratedSection, Document } from './types';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [sections, setSections] = useState<GeneratedSection[]>([]);
  const [globalWarnings, setGlobalWarnings] = useState<string[]>([]);
  const [regeneratingSection, setRegeneratingSection] = useState<string | null>(null);

  // Document hooks
  const { data: documentsData, isLoading: isLoadingDocuments } = useDocuments();
  const uploadMutation = useUploadDocument();
  const deleteMutation = useDeleteDocument();

  // Generation hooks
  const generateMutation = useGenerateDraft();
  const regenerateMutation = useRegenerateSection();

  const documents = documentsData?.documents ?? [];

  // Handle file upload
  const handleFileUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      try {
        await uploadMutation.mutateAsync({ file });
        e.target.value = ''; // Reset input
      } catch (error) {
        console.error('Upload failed:', error);
      }
    },
    [uploadMutation]
  );

  // Handle document deletion
  const handleDeleteDocument = useCallback(
    async (documentId: string) => {
      try {
        await deleteMutation.mutateAsync(documentId);
      } catch (error) {
        console.error('Delete failed:', error);
      }
    },
    [deleteMutation]
  );

  // Handle generation
  const handleGenerate = useCallback(async () => {
    if (!prompt.trim()) return;

    try {
      const result = await generateMutation.mutateAsync({ prompt });
      setSections(result.sections);

      // Collect global warnings from retrieval
      const warnings: string[] = [];
      if (result.retrieval_metadata.chunks_retrieved === 0) {
        warnings.push('No documents were found for your prompt. Upload relevant documents first.');
      }
      setGlobalWarnings(warnings);
    } catch (error) {
      console.error('Generation failed:', error);
      setGlobalWarnings([`Generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`]);
    }
  }, [prompt, generateMutation]);

  // Handle section content change
  const handleSectionChange = useCallback((sectionId: string, content: string) => {
    setSections((prev) =>
      prev.map((section) =>
        section.section_id === sectionId
          ? { ...section, content, is_user_edited: true }
          : section
      )
    );
  }, []);

  // Handle section regeneration
  const handleRegenerate = useCallback(
    async (sectionId: string) => {
      setRegeneratingSection(sectionId);

      try {
        const result = await regenerateMutation.mutateAsync({
          section_id: sectionId,
          prompt: prompt,
        });

        setSections((prev) =>
          prev.map((section) =>
            section.section_id === sectionId ? result.section : section
          )
        );
      } catch (error) {
        console.error('Regeneration failed:', error);
      } finally {
        setRegeneratingSection(null);
      }
    },
    [prompt, regenerateMutation]
  );

  // Handle section accept (currently just marks as not edited)
  const handleAccept = useCallback((sectionId: string) => {
    setSections((prev) =>
      prev.map((section) =>
        section.section_id === sectionId
          ? { ...section, is_user_edited: false }
          : section
      )
    );
  }, []);

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">RAG Writing Assistant</h1>
      </header>

      <div className="app__layout">
        {/* Left Sidebar - Document Management */}
        <aside className="app__sidebar">
          <section className="sidebar-section">
            <h2 className="sidebar-section__title">Documents</h2>

            <div className="upload-area">
              <label className="upload-area__label">
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={handleFileUpload}
                  disabled={uploadMutation.isPending}
                  className="upload-area__input"
                />
                <span className="upload-area__text">
                  {uploadMutation.isPending ? 'Uploading...' : 'Upload Document'}
                </span>
              </label>
              <p className="upload-area__hint">PDF, DOCX, or TXT</p>
            </div>

            <div className="document-list">
              {isLoadingDocuments ? (
                <p className="document-list__loading">Loading documents...</p>
              ) : documents.length === 0 ? (
                <p className="document-list__empty">No documents uploaded yet.</p>
              ) : (
                documents.map((doc) => (
                  <DocumentCard
                    key={doc.document_id}
                    document={doc}
                    onDelete={() => handleDeleteDocument(doc.document_id)}
                    isDeleting={deleteMutation.isPending}
                  />
                ))
              )}
            </div>
          </section>
        </aside>

        {/* Main Content */}
        <main className="app__main">
          {/* Prompt Input */}
          <section className="prompt-section">
            <label className="prompt-section__label" htmlFor="prompt-input">
              What would you like to write about?
            </label>
            <div className="prompt-section__input-group">
              <textarea
                id="prompt-input"
                className="prompt-section__textarea"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Enter your writing prompt here..."
                rows={3}
              />
              <button
                type="button"
                className="prompt-section__button"
                onClick={handleGenerate}
                disabled={!prompt.trim() || generateMutation.isPending}
              >
                {generateMutation.isPending ? 'Generating...' : 'Generate Draft'}
              </button>
            </div>
          </section>

          {/* Global Warnings */}
          {globalWarnings.length > 0 && (
            <WarningBanner warnings={globalWarnings} />
          )}

          {/* Document Editor */}
          <section className="editor-section">
            <DocumentEditor
              sections={sections}
              onSectionChange={handleSectionChange}
              onRegenerate={handleRegenerate}
              onAccept={handleAccept}
              regeneratingSection={regeneratingSection}
            />
          </section>
        </main>
      </div>
    </div>
  );
}

interface DocumentCardProps {
  document: Document;
  onDelete: () => void;
  isDeleting: boolean;
}

function DocumentCard({ document, onDelete, isDeleting }: DocumentCardProps) {
  return (
    <article className="document-card">
      <div className="document-card__info">
        <h3 className="document-card__title">{document.metadata.title}</h3>
        <p className="document-card__meta">
          {document.chunk_count} chunks | {document.document_type.toUpperCase()}
        </p>
        <span
          className={`document-card__status document-card__status--${document.status}`}
        >
          {document.status}
        </span>
      </div>
      <button
        type="button"
        className="document-card__delete"
        onClick={onDelete}
        disabled={isDeleting}
        aria-label={`Delete ${document.metadata.title}`}
      >
        Delete
      </button>
    </article>
  );
}

export default App;
