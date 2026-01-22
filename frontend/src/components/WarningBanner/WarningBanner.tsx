/**
 * WarningBanner - displays warnings about generated content.
 *
 * Design principle: Neutral guidance, not alarming alerts. These are
 * informational notices to help users make informed decisions.
 */

import './WarningBanner.css';

interface WarningBannerProps {
  warnings: string[];
  variant?: 'info' | 'caution';
}

export function WarningBanner({ warnings, variant = 'caution' }: WarningBannerProps) {
  if (warnings.length === 0) {
    return null;
  }

  return (
    <aside
      className={`warning-banner warning-banner--${variant}`}
      role="alert"
      aria-live="polite"
    >
      <header className="warning-banner__header">
        <span className="warning-banner__icon" aria-hidden="true">
          {variant === 'caution' ? '!' : 'i'}
        </span>
        <span className="warning-banner__title">
          {warnings.length === 1 ? 'Notice' : `${warnings.length} Notices`}
        </span>
      </header>

      <ul className="warning-banner__list">
        {warnings.map((warning, index) => (
          <li key={index} className="warning-banner__item">
            {formatWarning(warning)}
          </li>
        ))}
      </ul>
    </aside>
  );
}

/**
 * Format warning messages for display.
 * Strips internal warning type prefixes and cleans up the message.
 */
function formatWarning(warning: string): string {
  // Remove warning type prefix (e.g., "insufficient_context: ")
  const colonIndex = warning.indexOf(':');
  if (colonIndex !== -1 && colonIndex < 30) {
    return warning.slice(colonIndex + 1).trim();
  }
  return warning;
}
