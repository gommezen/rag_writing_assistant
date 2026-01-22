/**
 * DocumentEditor - the main editor component for generated documents.
 *
 * Design principles:
 * - Distinguishes AI-generated content from user-edited content
 * - Shows sources and confidence for each section
 * - Allows section-level regeneration and editing
 */

import { useState, useCallback } from 'react';
import type { GeneratedSection } from '../../types';
import { ConfidenceIndicator } from '../ConfidenceIndicator';
import { GenerationControls } from '../GenerationControls';
import { SourceCard } from '../SourceCard';
import { WarningBanner } from '../WarningBanner';
import './DocumentEditor.css';

interface DocumentEditorProps {
  sections: GeneratedSection[];
  onSectionChange: (sectionId: string, content: string) => void;
  onRegenerate: (sectionId: string) => void;
  onAccept: (sectionId: string) => void;
  onRevert?: (sectionId: string) => void;
  regeneratingSection?: string | null;
}

export function DocumentEditor({
  sections,
  onSectionChange,
  onRegenerate,
  onAccept,
  onRevert,
  regeneratingSection,
}: DocumentEditorProps) {
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(
    sections[0]?.section_id ?? null
  );

  const selectedSection = sections.find((s) => s.section_id === selectedSectionId);

  const handleSectionClick = useCallback((sectionId: string) => {
    setSelectedSectionId(sectionId);
  }, []);

  const handleContentChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>, sectionId: string) => {
      onSectionChange(sectionId, e.target.value);
    },
    [onSectionChange]
  );

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
            onClick={() => handleSectionClick(section.section_id)}
            onChange={(e) => handleContentChange(e, section.section_id)}
            onRegenerate={onRegenerate}
            onAccept={onAccept}
            {...(onRevert ? { onRevert } : {})}
          />
        ))}
      </div>

      <aside className="document-editor__sidebar">
        {selectedSection && (
          <SectionDetails section={selectedSection} />
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
  onClick: () => void;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onRegenerate: (sectionId: string) => void;
  onAccept: (sectionId: string) => void;
  onRevert?: (sectionId: string) => void;
}

function SectionEditor({
  section,
  index,
  isSelected,
  isRegenerating,
  onClick,
  onChange,
  onRegenerate,
  onAccept,
  onRevert,
}: SectionEditorProps) {
  return (
    <section
      className={`section-editor ${isSelected ? 'section-editor--selected' : ''} ${
        section.is_user_edited ? 'section-editor--edited' : ''
      }`}
      onClick={onClick}
      aria-label={`Section ${index + 1}`}
    >
      <header className="section-editor__header">
        <span className="section-editor__label">
          Section {index + 1}
          {section.is_user_edited && (
            <span className="section-editor__edited-badge">Edited</span>
          )}
        </span>
        <ConfidenceIndicator level={section.confidence} />
      </header>

      <textarea
        className="section-editor__textarea"
        value={section.content}
        onChange={onChange}
        placeholder="Section content..."
        disabled={isRegenerating}
        aria-label={`Content for section ${index + 1}`}
      />

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
}

function SectionDetails({ section }: SectionDetailsProps) {
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
              source={source}
              index={index + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
