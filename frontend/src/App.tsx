/**
 * Main App component for the RAG Writing Assistant.
 *
 * Layout: Three-panel design
 * - Left sidebar: Document management
 * - Center: Document editor
 * - Right sidebar: Source details (part of DocumentEditor)
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { Sun, Moon, ChevronLeft, ChevronRight, Download, Copy, Check, Eye, Lightbulb } from 'lucide-react';
import { DocumentEditor } from './components/DocumentEditor';
import { DocumentPreview } from './components/DocumentPreview';
import { WarningBanner } from './components/WarningBanner';
import {
  useDocuments,
  useDocumentChunks,
  useUploadDocument,
  useDocumentPolling,
  useDeleteDocument,
  useGenerateDraft,
  useRegenerateSection,
  useSuggestedQuestions,
} from './hooks';
import type { GeneratedSection, Document } from './types';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [sections, setSections] = useState<GeneratedSection[]>([]);
  const [globalWarnings, setGlobalWarnings] = useState<string[]>([]);
  const [regeneratingSection, setRegeneratingSection] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [acceptedSection, setAcceptedSection] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [copied, setCopied] = useState(false);
  const [previewDocumentId, setPreviewDocumentId] = useState<string | null>(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [promptHighlighted, setPromptHighlighted] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme');
    return saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches);
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const promptTextareaRef = useRef<HTMLTextAreaElement>(null);

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
    localStorage.setItem('theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  // Document hooks
  const { data: documentsData, isLoading: isLoadingDocuments } = useDocuments();
  const { uploadedDocumentId, clearUploadedDocumentId, ...uploadMutation } = useUploadDocument();
  const deleteMutation = useDeleteDocument();

  // Poll for document processing completion
  const { data: polledDocument } = useDocumentPolling(uploadedDocumentId);

  // Clear polling when document reaches terminal state
  useEffect(() => {
    if (polledDocument?.status === 'ready' || polledDocument?.status === 'failed') {
      clearUploadedDocumentId();
    }
  }, [polledDocument?.status, clearUploadedDocumentId]);

  // Generation hooks
  const generateMutation = useGenerateDraft();
  const regenerateMutation = useRegenerateSection();
  const suggestionsMutation = useSuggestedQuestions();

  // Document preview
  const { data: chunksData, isLoading: isLoadingChunks } = useDocumentChunks(previewDocumentId);
  const previewDocument = previewDocumentId
    ? documentsData?.documents.find((d) => d.document_id === previewDocumentId)
    : null;

  const documents = documentsData?.documents ?? [];

  // Handle file upload (from input or drag & drop)
  const uploadFile = useCallback(
    async (file: File) => {
      const validTypes = ['.pdf', '.docx', '.txt'];
      const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
      if (!validTypes.includes(ext)) {
        setGlobalWarnings(['Invalid file type. Please upload PDF, DOCX, or TXT files.']);
        return;
      }

      try {
        await uploadMutation.mutateAsync({ file });
      } catch (error) {
        console.error('Upload failed:', error);
      }
    },
    [uploadMutation]
  );

  const handleFileUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      await uploadFile(file);
      e.target.value = ''; // Reset input
    },
    [uploadFile]
  );

  // Drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      const file = e.dataTransfer.files?.[0];
      if (file) {
        await uploadFile(file);
      }
    },
    [uploadFile]
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

      // Find the current section content
      const currentSection = sections.find((s) => s.section_id === sectionId);
      if (!currentSection) {
        setRegeneratingSection(null);
        return;
      }

      try {
        const request = {
          section_id: sectionId,
          original_content: currentSection.content,
          ...(prompt ? { refinement_prompt: prompt } : {}),
        };
        const result = await regenerateMutation.mutateAsync(request);

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
    [prompt, sections, regenerateMutation]
  );

  // Handle section accept with visual feedback
  const handleAccept = useCallback((sectionId: string) => {
    setSections((prev) =>
      prev.map((section) =>
        section.section_id === sectionId
          ? { ...section, is_user_edited: false }
          : section
      )
    );
    // Show accepted feedback briefly
    setAcceptedSection(sectionId);
    setTimeout(() => setAcceptedSection(null), 1500);
  }, []);

  // Handle export generated content as TXT
  const handleExport = useCallback(() => {
    if (sections.length === 0) return;
    const content = sections.map((s) => s.content).join('\n\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'generated-content.txt';
    a.click();
    URL.revokeObjectURL(url);
  }, [sections]);

  // Handle copy to clipboard
  const handleCopy = useCallback(async () => {
    if (sections.length === 0) return;
    const content = sections.map((s) => s.content).join('\n\n');
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [sections]);

  // Handle generating suggested questions
  const handleGenerateSuggestions = useCallback(async () => {
    try {
      const result = await suggestionsMutation.mutateAsync({});
      setSuggestedQuestions(result.questions);
    } catch (error) {
      console.error('Failed to generate suggestions:', error);
    }
  }, [suggestionsMutation]);

  // Handle clicking on a suggested question
  const handleSuggestionClick = useCallback((question: string) => {
    setPrompt(question);
    // Focus the textarea and show highlight
    promptTextareaRef.current?.focus();
    setPromptHighlighted(true);
    setTimeout(() => setPromptHighlighted(false), 1500);
  }, []);

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">RAG Writing Assistant</h1>
        <button
          type="button"
          className="theme-toggle"
          onClick={() => setDarkMode((prev) => !prev)}
          aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {darkMode ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </header>

      <div className={`app__layout ${sidebarCollapsed ? 'app__layout--collapsed' : ''}`}>
        {/* Left Sidebar - Document Management */}
        <aside className={`app__sidebar ${sidebarCollapsed ? 'app__sidebar--collapsed' : ''}`}>
          <section className="sidebar-section">
            <div className="sidebar-section__header">
              <h2 className={`sidebar-section__title ${sidebarCollapsed ? 'sidebar-section__title--hidden' : ''}`}>Documents</h2>
              <button
                type="button"
                className="sidebar-collapse-btn"
                onClick={() => setSidebarCollapsed((prev) => !prev)}
                aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              >
                {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
              </button>
            </div>

            {!sidebarCollapsed && (
              <div
                className={`upload-area ${isDragOver ? 'upload-area--drag-over' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <label className="upload-area__label">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={handleFileUpload}
                    disabled={uploadMutation.isPending}
                    className="upload-area__input"
                  />
                  <span className="upload-area__text">
                    {uploadMutation.isPending
                      ? 'Uploading...'
                      : isDragOver
                      ? 'Drop file here'
                      : 'Upload Document'}
                  </span>
                </label>
                <p className="upload-area__hint">PDF, DOCX, or TXT</p>
              </div>
            )}

            <div className={`document-list ${sidebarCollapsed ? 'document-list--collapsed' : ''}`}>
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
                    onPreview={() => setPreviewDocumentId(doc.document_id)}
                    isDeleting={deleteMutation.isPending}
                  />
                ))
              )}
            </div>

            {/* Suggested Questions */}
            {!sidebarCollapsed && documents.length > 0 && (
              <div className="suggestions-section">
                <div className="suggestions-section__header">
                  <h3 className="suggestions-section__title">Suggested Questions</h3>
                  <button
                    type="button"
                    className="suggestions-section__generate"
                    onClick={handleGenerateSuggestions}
                    disabled={suggestionsMutation.isPending}
                    aria-label="Generate suggested questions"
                  >
                    <Lightbulb size={16} />
                    {suggestionsMutation.isPending ? 'Generating...' : 'Generate'}
                  </button>
                </div>
                {suggestedQuestions.length > 0 && (
                  <ul className="suggestions-list">
                    {suggestedQuestions.map((question, index) => (
                      <li key={index} className="suggestions-list__item">
                        <button
                          type="button"
                          className="suggestions-list__button"
                          onClick={() => handleSuggestionClick(question)}
                        >
                          {question}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
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
                ref={promptTextareaRef}
                id="prompt-input"
                className={`prompt-section__textarea${promptHighlighted ? ' prompt-section__textarea--highlighted' : ''}`}
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
            {sections.length > 0 && (
              <div className="editor-section__header">
                <button
                  type="button"
                  className={`copy-btn ${copied ? 'copy-btn--copied' : ''}`}
                  onClick={handleCopy}
                  aria-label="Copy content to clipboard"
                >
                  {copied ? <Check size={16} /> : <Copy size={16} />}
                  <span>{copied ? 'Copied!' : 'Copy'}</span>
                </button>
                <button
                  type="button"
                  className="export-btn"
                  onClick={handleExport}
                  aria-label="Export content as text file"
                >
                  <Download size={16} />
                  <span>Export TXT</span>
                </button>
              </div>
            )}
            <DocumentEditor
              sections={sections}
              onSectionChange={handleSectionChange}
              onRegenerate={handleRegenerate}
              onAccept={handleAccept}
              regeneratingSection={regeneratingSection}
              acceptedSection={acceptedSection}
            />
          </section>
        </main>
      </div>

      {/* Document Preview Modal */}
      {previewDocumentId && previewDocument && (
        <DocumentPreview
          documentTitle={previewDocument.metadata.title}
          chunks={chunksData?.chunks ?? []}
          isLoading={isLoadingChunks}
          onClose={() => setPreviewDocumentId(null)}
        />
      )}
    </div>
  );
}

interface DocumentCardProps {
  document: Document;
  onDelete: () => void;
  onPreview: () => void;
  isDeleting: boolean;
}

function DocumentCard({ document, onDelete, onPreview, isDeleting }: DocumentCardProps) {
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
      <div className="document-card__actions">
        <button
          type="button"
          className="document-card__preview"
          onClick={onPreview}
          disabled={document.status !== 'ready'}
          aria-label={`Preview ${document.metadata.title}`}
        >
          <Eye size={14} />
        </button>
        <button
          type="button"
          className="document-card__delete"
          onClick={onDelete}
          disabled={isDeleting}
          aria-label={`Delete ${document.metadata.title}`}
        >
          Delete
        </button>
      </div>
    </article>
  );
}

export default App;
