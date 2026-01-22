/**
 * Tests for ConfidenceIndicator component.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfidenceIndicator } from './ConfidenceIndicator';

describe('ConfidenceIndicator', () => {
  describe('rendering confidence levels', () => {
    it('renders high confidence correctly', () => {
      render(<ConfidenceIndicator level="high" />);

      expect(screen.getByText('High')).toBeInTheDocument();
    });

    it('renders medium confidence correctly', () => {
      render(<ConfidenceIndicator level="medium" />);

      expect(screen.getByText('Medium')).toBeInTheDocument();
    });

    it('renders low confidence correctly', () => {
      render(<ConfidenceIndicator level="low" />);

      expect(screen.getByText('Low')).toBeInTheDocument();
    });

    it('renders unknown confidence correctly', () => {
      render(<ConfidenceIndicator level="unknown" />);

      expect(screen.getByText('Unknown')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has accessible aria-label for high confidence', () => {
      render(<ConfidenceIndicator level="high" />);

      const indicator = screen.getByRole('status');
      expect(indicator).toHaveAttribute(
        'aria-label',
        'Confidence level: High. Well-supported by multiple sources'
      );
    });

    it('has accessible aria-label for medium confidence', () => {
      render(<ConfidenceIndicator level="medium" />);

      const indicator = screen.getByRole('status');
      expect(indicator).toHaveAttribute(
        'aria-label',
        'Confidence level: Medium. Supported by sources, verify key claims'
      );
    });

    it('has accessible aria-label for low confidence', () => {
      render(<ConfidenceIndicator level="low" />);

      const indicator = screen.getByRole('status');
      expect(indicator).toHaveAttribute(
        'aria-label',
        'Confidence level: Low. Limited source support, review carefully'
      );
    });

    it('has accessible aria-label for unknown confidence', () => {
      render(<ConfidenceIndicator level="unknown" />);

      const indicator = screen.getByRole('status');
      expect(indicator).toHaveAttribute(
        'aria-label',
        'Confidence level: Unknown. Could not determine confidence level'
      );
    });

    it('has role="status" for screen readers', () => {
      render(<ConfidenceIndicator level="high" />);

      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });

  describe('label visibility', () => {
    it('shows label by default', () => {
      render(<ConfidenceIndicator level="high" />);

      expect(screen.getByText('High')).toBeInTheDocument();
    });

    it('shows label when showLabel is true', () => {
      render(<ConfidenceIndicator level="high" showLabel={true} />);

      expect(screen.getByText('High')).toBeInTheDocument();
    });

    it('hides label when showLabel is false', () => {
      render(<ConfidenceIndicator level="high" showLabel={false} />);

      expect(screen.queryByText('High')).not.toBeInTheDocument();
    });
  });

  describe('CSS classes', () => {
    it('applies correct class for high confidence', () => {
      const { container } = render(<ConfidenceIndicator level="high" />);

      expect(container.querySelector('.confidence-indicator--high')).toBeInTheDocument();
    });

    it('applies correct class for medium confidence', () => {
      const { container } = render(<ConfidenceIndicator level="medium" />);

      expect(container.querySelector('.confidence-indicator--medium')).toBeInTheDocument();
    });

    it('applies correct class for low confidence', () => {
      const { container } = render(<ConfidenceIndicator level="low" />);

      expect(container.querySelector('.confidence-indicator--low')).toBeInTheDocument();
    });

    it('applies correct class for unknown confidence', () => {
      const { container } = render(<ConfidenceIndicator level="unknown" />);

      expect(container.querySelector('.confidence-indicator--unknown')).toBeInTheDocument();
    });
  });

  describe('tooltip', () => {
    it('has description as title attribute for high confidence', () => {
      render(<ConfidenceIndicator level="high" />);

      const indicator = screen.getByRole('status');
      expect(indicator).toHaveAttribute('title', 'Well-supported by multiple sources');
    });

    it('has description as title attribute for low confidence', () => {
      render(<ConfidenceIndicator level="low" />);

      const indicator = screen.getByRole('status');
      expect(indicator).toHaveAttribute('title', 'Limited source support, review carefully');
    });
  });

  describe('visual dot', () => {
    it('renders a visual dot element', () => {
      const { container } = render(<ConfidenceIndicator level="high" />);

      expect(container.querySelector('.confidence-indicator__dot')).toBeInTheDocument();
    });

    it('dot has aria-hidden for accessibility', () => {
      const { container } = render(<ConfidenceIndicator level="high" />);

      const dot = container.querySelector('.confidence-indicator__dot');
      expect(dot).toHaveAttribute('aria-hidden', 'true');
    });
  });
});
