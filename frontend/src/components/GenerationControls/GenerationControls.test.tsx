/**
 * Tests for GenerationControls component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GenerationControls } from './GenerationControls';

describe('GenerationControls', () => {
  const defaultProps = {
    sectionId: 'section-1',
    isUserEdited: false,
    onRegenerate: vi.fn(),
    onAccept: vi.fn(),
  };

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('button rendering', () => {
    it('renders Regenerate and Accept buttons', () => {
      render(<GenerationControls {...defaultProps} />);

      expect(screen.getByRole('button', { name: 'Regenerate' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Accept' })).toBeInTheDocument();
    });

    it('shows Revert button when user has edited', () => {
      render(
        <GenerationControls
          {...defaultProps}
          isUserEdited={true}
          onRevert={vi.fn()}
        />
      );

      expect(screen.getByRole('button', { name: 'Revert Changes' })).toBeInTheDocument();
    });

    it('does not show Revert button when user has not edited', () => {
      render(<GenerationControls {...defaultProps} isUserEdited={false} />);

      expect(screen.queryByRole('button', { name: 'Revert Changes' })).not.toBeInTheDocument();
    });

    it('does not show Revert button when onRevert is not provided', () => {
      render(<GenerationControls {...defaultProps} isUserEdited={true} />);

      expect(screen.queryByRole('button', { name: 'Revert Changes' })).not.toBeInTheDocument();
    });
  });

  describe('button interactions', () => {
    it('calls onRegenerate with sectionId when Regenerate is clicked', () => {
      const onRegenerate = vi.fn();
      render(<GenerationControls {...defaultProps} onRegenerate={onRegenerate} />);

      fireEvent.click(screen.getByRole('button', { name: 'Regenerate' }));

      expect(onRegenerate).toHaveBeenCalledWith('section-1');
    });

    it('calls onAccept with sectionId when Accept is clicked', () => {
      const onAccept = vi.fn();
      render(<GenerationControls {...defaultProps} onAccept={onAccept} />);

      fireEvent.click(screen.getByRole('button', { name: 'Accept' }));

      expect(onAccept).toHaveBeenCalledWith('section-1');
    });

    it('calls onRevert with sectionId when Revert is clicked', () => {
      const onRevert = vi.fn();
      render(
        <GenerationControls
          {...defaultProps}
          isUserEdited={true}
          onRevert={onRevert}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: 'Revert Changes' }));

      expect(onRevert).toHaveBeenCalledWith('section-1');
    });
  });

  describe('regenerating state', () => {
    it('disables Regenerate button when regenerating', () => {
      render(<GenerationControls {...defaultProps} isRegenerating={true} />);

      expect(screen.getByRole('button', { name: 'Regenerating...' })).toBeDisabled();
    });

    it('disables Accept button when regenerating', () => {
      render(<GenerationControls {...defaultProps} isRegenerating={true} />);

      expect(screen.getByRole('button', { name: 'Accept' })).toBeDisabled();
    });

    it('disables Revert button when regenerating', () => {
      render(
        <GenerationControls
          {...defaultProps}
          isUserEdited={true}
          isRegenerating={true}
          onRevert={vi.fn()}
        />
      );

      expect(screen.getByRole('button', { name: 'Revert Changes' })).toBeDisabled();
    });

    it('shows "Regenerating..." text when regenerating', () => {
      render(<GenerationControls {...defaultProps} isRegenerating={true} />);

      expect(screen.getByRole('button', { name: 'Regenerating...' })).toBeInTheDocument();
    });

    it('has aria-busy attribute when regenerating', () => {
      render(<GenerationControls {...defaultProps} isRegenerating={true} />);

      const regenerateButton = screen.getByRole('button', { name: 'Regenerating...' });
      expect(regenerateButton).toHaveAttribute('aria-busy', 'true');
    });
  });

  describe('accessibility', () => {
    it('has role="group" for the control container', () => {
      render(<GenerationControls {...defaultProps} />);

      expect(screen.getByRole('group')).toBeInTheDocument();
    });

    it('has aria-label for the control group', () => {
      render(<GenerationControls {...defaultProps} />);

      expect(screen.getByRole('group')).toHaveAttribute('aria-label', 'Section controls');
    });

    it('all buttons have type="button"', () => {
      render(
        <GenerationControls
          {...defaultProps}
          isUserEdited={true}
          onRevert={vi.fn()}
        />
      );

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button).toHaveAttribute('type', 'button');
      });
    });
  });

  describe('button states', () => {
    it('buttons are enabled when not regenerating', () => {
      render(<GenerationControls {...defaultProps} isRegenerating={false} />);

      expect(screen.getByRole('button', { name: 'Regenerate' })).not.toBeDisabled();
      expect(screen.getByRole('button', { name: 'Accept' })).not.toBeDisabled();
    });
  });
});
