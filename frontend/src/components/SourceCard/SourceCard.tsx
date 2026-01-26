/**
 * SourceCard - displays a retrieved source with its metadata.
 *
 * Design principle: Sources visible by default. Users should always be able
 * to see and verify where generated content comes from.
 */

import { forwardRef } from 'react';
import type { SourceReference } from '../../types';
import './SourceCard.css';

interface SourceCardProps {
  source: SourceReference;
  index: number;
  isHighlighted?: boolean;
  onClick?: () => void;
}

export const SourceCard = forwardRef<HTMLElement, SourceCardProps>(function SourceCard(
  { source, index, isHighlighted = false, onClick },
  ref
) {
  const relevancePercent = Math.round(source.relevance_score * 100);
  const documentTitle = source.metadata['title'] ?? 'Untitled';

  return (
    <article
      ref={ref}
      className={`source-card ${isHighlighted ? 'source-card--highlighted' : ''}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      <header className="source-card__header">
        <span className="source-card__index">[Source {index}]</span>
        <span
          className="source-card__relevance"
          title={`Relevance score: ${source.relevance_score.toFixed(3)}`}
        >
          {relevancePercent}% match
        </span>
      </header>

      <h3 className="source-card__title">{documentTitle}</h3>

      <blockquote className="source-card__excerpt">
        {source.excerpt}
      </blockquote>

      {Object.keys(source.metadata).length > 0 && (
        <footer className="source-card__metadata">
          {source.metadata['filename'] && (
            <span className="source-card__meta-item">
              {source.metadata['filename']}
            </span>
          )}
        </footer>
      )}
    </article>
  );
});
