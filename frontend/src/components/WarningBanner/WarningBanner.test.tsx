/**
 * Tests for WarningBanner component.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WarningBanner } from './WarningBanner';

describe('WarningBanner', () => {
  it('returns null for empty warnings array', () => {
    const { container } = render(<WarningBanner warnings={[]} />);

    expect(container.firstChild).toBeNull();
  });

  it('renders single warning', () => {
    render(<WarningBanner warnings={['This is a warning message']} />);

    expect(screen.getByText('Notice')).toBeInTheDocument();
    expect(screen.getByText('This is a warning message')).toBeInTheDocument();
  });

  it('renders multiple warnings with count', () => {
    const warnings = [
      'First warning message',
      'Second warning message',
      'Third warning message',
    ];

    render(<WarningBanner warnings={warnings} />);

    expect(screen.getByText('3 Notices')).toBeInTheDocument();
    warnings.forEach((warning) => {
      expect(screen.getByText(warning)).toBeInTheDocument();
    });
  });

  it('has role="alert" for accessibility', () => {
    render(<WarningBanner warnings={['Test warning']} />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('has aria-live="polite" attribute', () => {
    render(<WarningBanner warnings={['Test warning']} />);

    const alert = screen.getByRole('alert');
    expect(alert).toHaveAttribute('aria-live', 'polite');
  });

  it('strips warning type prefix from message', () => {
    render(
      <WarningBanner warnings={['insufficient_context: No relevant sources found']} />
    );

    expect(screen.getByText('No relevant sources found')).toBeInTheDocument();
    expect(screen.queryByText('insufficient_context:')).not.toBeInTheDocument();
  });

  it('keeps message intact if no prefix pattern', () => {
    render(<WarningBanner warnings={['A warning without a prefix']} />);

    expect(screen.getByText('A warning without a prefix')).toBeInTheDocument();
  });

  it('renders with caution variant by default', () => {
    const { container } = render(<WarningBanner warnings={['Warning']} />);

    expect(container.querySelector('.warning-banner--caution')).toBeInTheDocument();
  });

  it('renders with info variant when specified', () => {
    const { container } = render(
      <WarningBanner warnings={['Info message']} variant="info" />
    );

    expect(container.querySelector('.warning-banner--info')).toBeInTheDocument();
  });

  it('renders caution icon for caution variant', () => {
    render(<WarningBanner warnings={['Warning']} variant="caution" />);

    const icon = document.querySelector('.warning-banner__icon');
    expect(icon?.textContent).toBe('!');
  });

  it('renders info icon for info variant', () => {
    render(<WarningBanner warnings={['Info']} variant="info" />);

    const icon = document.querySelector('.warning-banner__icon');
    expect(icon?.textContent).toBe('i');
  });

  it('handles warning with colon but long prefix (keeps intact)', () => {
    // Prefix longer than 30 chars should not be stripped
    render(
      <WarningBanner
        warnings={['this_is_a_very_long_prefix_that_exceeds_limit: message']}
      />
    );

    expect(
      screen.getByText('this_is_a_very_long_prefix_that_exceeds_limit: message')
    ).toBeInTheDocument();
  });
});
