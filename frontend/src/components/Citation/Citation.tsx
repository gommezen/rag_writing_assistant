/**
 * Citation - interactive inline citation component.
 *
 * Renders [Source N] as clickable spans with hover tooltips.
 * Supports the governance principle of making AI behavior understandable
 * by allowing users to quickly verify source references.
 */

import { useState, useRef, useCallback } from 'react';
import type { SourceReference } from '../../types';
import { CitationTooltip } from './CitationTooltip';
import './Citation.css';

export interface CitationProps {
  /** 1-based citation number */
  index: number;
  /** Source data for tooltip display */
  source: SourceReference | undefined;
  /** Called when citation is clicked */
  onActivate?: (index: number) => void;
}

export function Citation({ index, source, onActivate }: CitationProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const citationRef = useRef<HTMLSpanElement>(null);

  const handleMouseEnter = useCallback(() => {
    if (citationRef.current) {
      const rect = citationRef.current.getBoundingClientRect();
      setTooltipPosition({
        x: rect.left + rect.width / 2,
        y: rect.top,
      });
    }
    setIsHovered(true);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setIsHovered(false);
  }, []);

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onActivate?.(index);
    },
    [index, onActivate]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onActivate?.(index);
      }
    },
    [index, onActivate]
  );

  return (
    <>
      <span
        ref={citationRef}
        className={`citation ${source ? 'citation--valid' : 'citation--invalid'}`}
        role="button"
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        aria-label={`Source ${index}${source ? `: ${source.metadata['title'] ?? 'Untitled'}` : ' (not found)'}`}
      >
        [Source {index}]
      </span>
      {isHovered && source && (
        <CitationTooltip
          source={source}
          position={tooltipPosition}
          visible={isHovered}
        />
      )}
    </>
  );
}
