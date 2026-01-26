/**
 * DocumentEditor - the main editor component for generated documents.
 *
 * Design principles:
 * - Distinguishes AI-generated content from user-edited content
 * - Shows sources and confidence for each section
 * - Allows section-level regeneration and editing
 * - Interactive citations link to source cards (governance: explain AI output)
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import type { GeneratedSection } from '../../types';
import { ConfidenceIndicator } from '../ConfidenceIndicator';
import { GenerationControls } from '../GenerationControls';
import { SourceCard } from '../SourceCard';
import { WarningBanner } from '../WarningBanner';
import { renderCitationsInText } from '../../utils/citationParser';
import './DocumentEditor.css';

interface DocumentEditorProps {
  sections: GeneratedSection[];
  onSectionChange: (sectionId: string, content: string) => void;
  onRegenerate: (sectionId: string) => void;
  onAccept: (sectionId: string) => void;
  onRevert?: (sectionId: string) => void;
  regeneratingSection?: string | null;
  acceptedSection?: string | null;
}

export function DocumentEditor({
  sections,
  onSectionChange,
  onRegenerate,
  onAccept,
  onRevert,
  regeneratingSection,
  acceptedSection,
}: DocumentEditorProps) {
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(
    sections[0]?.section_id ?? null
  );
  const [highlightedSourceIndex, setHighlightedSourceIndex] = useState<number | null>(null);
  const [editingSectionId, setEditingSectionId] = useState<string | null>(null);

  // Refs for source cards to enable scroll-to-source
  const sourceRefs = useRef<Map<number, HTMLElement>>(new Map());

  // Update selection when sections change (e.g., new generation)
  useEffect(() => {
    const firstSection = sections[0];
    if (firstSection) {
      // If current selection doesn't exist in new sections, select first
      const currentExists = sections.some((s) => s.section_id === selectedSectionId);
      if (!currentExists) {
        setSelectedSectionId(firstSection.section_id);
      }
    } else {
      setSelectedSectionId(null);
    }
  }, [sections, selectedSectionId]);

  const selectedSection = sections.find((s) => s.section_id === selectedSectionId);

  const handleSectionClick = useCallback((sectionId: string) => {
    setSelectedSectionId(sectionId);
  }, []);

  const handleCitationClick = useCallback((index: number) => {
    // Highlight the source card
    setHighlightedSourceIndex(index);

    // Scroll to the source card
    const sourceRef = sourceRefs.current.get(index);
    if (sourceRef) {
      sourceRef.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // Clear highlight after animation
    setTimeout(() => setHighlightedSourceIndex(null), 2000);
  }, []);

  const handleEditToggle = useCallback((sectionId: string) => {
    setEditingSectionId((prev) => (prev === sectionId ? null : sectionId));
  }, []);

  const handleEditSave = useCallback((sectionId: string, content: string) => {
    onSectionChange(sectionId, content);
    setEditingSectionId(null);
  }, [onSectionChange]);

  // Clear source refs when section changes
  useEffect(() => {
    sourceRefs.current.clear();
  }, [selectedSectionId]);

  if (sections.length === 0) {
    return (
      <div className="document-editor document-editor--empty">
        <p className="document-editor__empty-message">
          No content generated yet. Enter a prompt to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="document-editor">
      <div className="document-editor__content">
        {sections.map((section, index) => (
          <SectionEditor
            key={section.section_id}
            section={section}
            index={index}
            isSelected={section.section_id === selectedSectionId}
            isRegenerating={regeneratingSection === section.section_id}
            isAccepted={acceptedSection === section.section_id}
            isEditing={editingSectionId === section.section_id}
            onClick={() => handleSectionClick(section.section_id)}
            onCitationClick={handleCitationClick}
            onEditToggle={() => handleEditToggle(section.section_id)}
            onEditSave={(content) => handleEditSave(section.section_id, content)}
            onRegenerate={onRegenerate}
            onAccept={onAccept}
            {...(onRevert ? { onRevert } : {})}
          />
        ))}
      </div>

      <aside className="document-editor__sidebar">
        {selectedSection && (
          <SectionDetails
            section={selectedSection}
            highlightedSourceIndex={highlightedSourceIndex}
            sourceRefs={sourceRefs}
          />
        )}
      </aside>
    </div>
  );
}

interface SectionEditorProps {
  section: GeneratedSection;
  index: number;
  isSelected: boolean;
  isRegenerating: boolean;
  isAccepted?: boolean;
  isEditing: boolean;
  onClick: () => void;
  onCitationClick: (index: number) => void;
  onEditToggle: () => void;
  onEditSave: (content: string) => void;
  onRegenerate: (sectionId: string) => void;
  onAccept: (sectionId: string) => void;
  onRevert?: (sectionId: string) => void;
}

function SectionEditor({
  section,
  index,
  isSelected,
  isRegenerating,
  isAccepted,
  isEditing,
  onClick,
  onCitationClick,
  onEditToggle,
  onEditSave,
  onRegenerate,
  onAccept,
  onRevert,
}: SectionEditorProps) {
  const [editContent, setEditContent] = useState(section.content);

  // Sync edit content when section content changes (e.g., after regeneration)
  useEffect(() => {
    setEditContent(section.content);
  }, [section.content]);

  const handleEditSave = () => {
    onEditSave(editContent);
  };

  const handleEditCancel = () => {
    setEditContent(section.content);
    onEditToggle();
  };

  return (
    <section
      className={`section-editor ${isSelected ? 'section-editor--selected' : ''} ${
        section.is_user_edited ? 'section-editor--edited' : ''
      } ${isAccepted ? 'section-editor--accepted' : ''}`}
      onClick={onClick}
      aria-label={section.title || `Section ${index + 1}`}
    >
      <header className="section-editor__header">
        <span className="section-editor__label">
          {section.title || `Section ${index + 1}`}
          {section.is_user_edited && (
            <span className="section-editor__edited-badge">Edited</span>
          )}
          {isAccepted && (
            <span className="section-editor__accepted-badge">Accepted!</span>
          )}
        </span>
        <div className="section-editor__header-actions">
          <ConfidenceIndicator level={section.confidence} />
          {!isEditing && !isRegenerating && (
            <button
              className="section-editor__edit-button"
              onClick={(e) => {
                e.stopPropagation();
                onEditToggle();
              }}
              aria-label="Edit section"
            >
              Edit
            </button>
          )}
        </div>
      </header>

      {isEditing ? (
        <div className="section-editor__edit-mode">
          <textarea
            className="section-editor__textarea"
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            placeholder="Section content..."
            disabled={isRegenerating}
            aria-label={`Edit content for ${section.title || `section ${index + 1}`}`}
            autoFocus
          />
          <div className="section-editor__edit-actions">
            <button
              className="section-editor__save-button"
              onClick={(e) => {
                e.stopPropagation();
                handleEditSave();
              }}
            >
              Save
            </button>
            <button
              className="section-editor__cancel-button"
              onClick={(e) => {
                e.stopPropagation();
                handleEditCancel();
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div
          className="section-editor__content"
          aria-label={`Content for ${section.title || `section ${index + 1}`}`}
        >
          {renderCitationsInText(section.content, section.sources, onCitationClick)}
        </div>
      )}

      {section.warnings.length > 0 && (
        <WarningBanner warnings={section.warnings} />
      )}

      <GenerationControls
        sectionId={section.section_id}
        isUserEdited={section.is_user_edited}
        isRegenerating={isRegenerating}
        onRegenerate={onRegenerate}
        onAccept={onAccept}
        {...(onRevert ? { onRevert } : {})}
      />
    </section>
  );
}

interface SectionDetailsProps {
  section: GeneratedSection;
  highlightedSourceIndex: number | null;
  sourceRefs: React.MutableRefObject<Map<number, HTMLElement>>;
}

function SectionDetails({ section, highlightedSourceIndex, sourceRefs }: SectionDetailsProps) {
  const setSourceRef = useCallback(
    (index: number) => (el: HTMLElement | null) => {
      if (el) {
        sourceRefs.current.set(index, el);
      } else {
        sourceRefs.current.delete(index);
      }
    },
    [sourceRefs]
  );

  return (
    <div className="section-details">
      <h2 className="section-details__title">Sources</h2>

      {section.sources.length === 0 ? (
        <p className="section-details__empty">
          No sources available for this section.
        </p>
      ) : (
        <div className="section-details__sources">
          {section.sources.map((source, index) => (
            <SourceCard
              key={source.chunk_id}
              ref={setSourceRef(index + 1)}
              source={source}
              index={index + 1}
              isHighlighted={highlightedSourceIndex === index + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
