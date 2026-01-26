/**
 * CitationTooltip - tooltip component for citation hover preview.
 *
 * Shows source excerpt, document title, and relevance score.
 * Positioned above or below the citation depending on viewport space.
 */

import { useEffect, useState } from 'react';
import type { SourceReference } from '../../types';
import './Citation.css';

interface CitationTooltipProps {
  source: SourceReference;
  position: { x: number; y: number };
  visible: boolean;
}

const MAX_EXCERPT_LENGTH = 150;

export function CitationTooltip({ source, position, visible }: CitationTooltipProps) {
  const [placement, setPlacement] = useState<'above' | 'below'>('above');

  useEffect(() => {
    // Auto-adjust placement based on viewport position
    const spaceAbove = position.y;
    const tooltipHeight = 120; // Approximate height

    if (spaceAbove < tooltipHeight + 20) {
      setPlacement('below');
    } else {
      setPlacement('above');
    }
  }, [position]);

  if (!visible) {
    return null;
  }

  const documentTitle = source.metadata['title'] ?? 'Untitled';
  const relevancePercent = Math.round(source.relevance_score * 100);

  // Truncate excerpt if too long
  const excerpt =
    source.excerpt.length > MAX_EXCERPT_LENGTH
      ? source.excerpt.substring(0, MAX_EXCERPT_LENGTH).trim() + '...'
      : source.excerpt;

  const tooltipStyle: React.CSSProperties = {
    left: position.x,
    top: placement === 'above' ? position.y : position.y + 24,
    transform: placement === 'above' ? 'translate(-50%, -100%)' : 'translate(-50%, 0)',
  };

  return (
    <div
      className={`citation-tooltip citation-tooltip--${placement}`}
      style={tooltipStyle}
      role="tooltip"
    >
      <div className="citation-tooltip__header">
        <span className="citation-tooltip__title">{documentTitle}</span>
        <span className="citation-tooltip__relevance">{relevancePercent}% match</span>
      </div>
      <p className="citation-tooltip__excerpt">{excerpt}</p>
    </div>
  );
}
