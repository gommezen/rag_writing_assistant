/**
 * ConfidenceIndicator - displays the confidence level of generated content.
 *
 * Design principle: Make uncertainty visible. Users should always know
 * how much to trust generated content.
 */

import type { ConfidenceLevel } from '../../types';
import './ConfidenceIndicator.css';

interface ConfidenceIndicatorProps {
  level: ConfidenceLevel;
  showLabel?: boolean;
}

const CONFIDENCE_CONFIG: Record<
  ConfidenceLevel,
  { label: string; description: string }
> = {
  high: {
    label: 'High',
    description: 'Well-supported by multiple sources',
  },
  medium: {
    label: 'Medium',
    description: 'Supported by sources, verify key claims',
  },
  low: {
    label: 'Low',
    description: 'Limited source support, review carefully',
  },
  unknown: {
    label: 'Unknown',
    description: 'Could not determine confidence level',
  },
};

export function ConfidenceIndicator({
  level,
  showLabel = true,
}: ConfidenceIndicatorProps) {
  const config = CONFIDENCE_CONFIG[level];

  return (
    <div
      className={`confidence-indicator confidence-indicator--${level}`}
      title={config.description}
      role="status"
      aria-label={`Confidence level: ${config.label}. ${config.description}`}
    >
      <span className="confidence-indicator__dot" aria-hidden="true" />
      {showLabel && (
        <span className="confidence-indicator__label">{config.label}</span>
      )}
    </div>
  );
}
