/**
 * GenerationControls - section-level controls for regeneration and editing.
 *
 * Design principle: Control over magic. Users can regenerate, edit, and
 * accept content at the section level without affecting other sections.
 */

import './GenerationControls.css';

interface GenerationControlsProps {
  sectionId: string;
  isUserEdited: boolean;
  isRegenerating?: boolean;
  onRegenerate: (sectionId: string) => void;
  onAccept: (sectionId: string) => void;
  onRevert?: (sectionId: string) => void;
}

export function GenerationControls({
  sectionId,
  isUserEdited,
  isRegenerating = false,
  onRegenerate,
  onAccept,
  onRevert,
}: GenerationControlsProps) {
  return (
    <div className="generation-controls" role="group" aria-label="Section controls">
      <button
        type="button"
        className="generation-controls__button generation-controls__button--primary"
        onClick={() => onRegenerate(sectionId)}
        disabled={isRegenerating}
        aria-busy={isRegenerating}
      >
        {isRegenerating ? 'Regenerating...' : 'Regenerate'}
      </button>

      <button
        type="button"
        className="generation-controls__button"
        onClick={() => onAccept(sectionId)}
        disabled={isRegenerating}
      >
        Accept
      </button>

      {isUserEdited && onRevert && (
        <button
          type="button"
          className="generation-controls__button generation-controls__button--secondary"
          onClick={() => onRevert(sectionId)}
          disabled={isRegenerating}
        >
          Revert Changes
        </button>
      )}
    </div>
  );
}
