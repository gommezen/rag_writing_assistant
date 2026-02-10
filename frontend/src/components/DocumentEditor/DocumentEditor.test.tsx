/**
 * Tests for DocumentEditor component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { DocumentEditor } from './DocumentEditor';
import { createMockSection, createMockSections, createMockSources } from '../../test/mocks';

describe('DocumentEditor', () => {
  const defaultProps = {
    sections: createMockSections(3),
    onSectionChange: vi.fn(),
    onRegenerate: vi.fn(),
    onAccept: vi.fn(),
  };

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('empty state', () => {
    it('renders empty state when no sections', () => {
      render(<DocumentEditor {...defaultProps} sections={[]} />);

      expect(
        screen.getByText('No content generated yet. Enter a prompt to get started.')
      ).toBeInTheDocument();
    });

    it('has empty class when no sections', () => {
      const { container } = render(<DocumentEditor {...defaultProps} sections={[]} />);

      expect(container.querySelector('.document-editor--empty')).toBeInTheDocument();
    });
  });

  describe('rendering sections', () => {
    it('renders all sections', () => {
      const sections = createMockSections(3);
      render(<DocumentEditor {...defaultProps} sections={sections} />);

      expect(screen.getByText('Section 1')).toBeInTheDocument();
      expect(screen.getByText('Section 2')).toBeInTheDocument();
      expect(screen.getByText('Section 3')).toBeInTheDocument();
    });

    it('renders section content', () => {
      const section = createMockSection({ content: 'Unique test content here' });
      render(<DocumentEditor {...defaultProps} sections={[section]} />);

      expect(screen.getByText('Unique test content here')).toBeInTheDocument();
    });
  });

  describe('section selection', () => {
    it('shows sources for selected section', () => {
      const sources = createMockSources(2);
      const section = createMockSection({ sources });
      const { container } = render(<DocumentEditor {...defaultProps} sections={[section]} />);

      // First section should be selected by default
      expect(screen.getByText('Sources')).toBeInTheDocument();
      // Source indices appear in both inline citations and sidebar cards; scope to sidebar
      const sidebar = container.querySelector('.document-editor__sidebar') as HTMLElement;
      expect(within(sidebar).getByText('[Source 1]')).toBeInTheDocument();
      expect(within(sidebar).getByText('[Source 2]')).toBeInTheDocument();
    });

    it('shows empty sources message when section has no sources', () => {
      const section = createMockSection({ sources: [] });
      render(<DocumentEditor {...defaultProps} sections={[section]} />);

      expect(screen.getByText('No sources available for this section.')).toBeInTheDocument();
    });

    it('selects first section by default', () => {
      const sections = createMockSections(3);
      const { container } = render(<DocumentEditor {...defaultProps} sections={sections} />);

      // First section should have selected class
      const firstSection = container.querySelector('.section-editor');
      expect(firstSection).toHaveClass('section-editor--selected');
    });
  });

  describe('section editing', () => {
    it('calls onSectionChange when edited', () => {
      const onSectionChange = vi.fn();
      const section = createMockSection({ section_id: 'sec-1', content: 'Original' });
      render(
        <DocumentEditor
          {...defaultProps}
          sections={[section]}
          onSectionChange={onSectionChange}
        />
      );

      // Enter edit mode
      fireEvent.click(screen.getByRole('button', { name: 'Edit section' }));

      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Updated content' } });

      // Save the edit
      fireEvent.click(screen.getByText('Save'));

      expect(onSectionChange).toHaveBeenCalledWith('sec-1', 'Updated content');
    });

    it('shows edited badge when section is user edited', () => {
      const section = createMockSection({ is_user_edited: true });
      render(<DocumentEditor {...defaultProps} sections={[section]} />);

      expect(screen.getByText('Edited')).toBeInTheDocument();
    });
  });

  describe('warnings', () => {
    it('shows warnings for sections', () => {
      const section = createMockSection({
        warnings: ['Warning: Low source coverage'],
      });
      render(<DocumentEditor {...defaultProps} sections={[section]} />);

      expect(screen.getByText('Low source coverage')).toBeInTheDocument();
    });

    it('does not show warning banner when no warnings', () => {
      const section = createMockSection({ warnings: [] });
      render(<DocumentEditor {...defaultProps} sections={[section]} />);

      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  describe('confidence indicator', () => {
    it('shows confidence indicator for each section', () => {
      const section = createMockSection({ confidence: 'high' });
      render(<DocumentEditor {...defaultProps} sections={[section]} />);

      expect(screen.getByText('High')).toBeInTheDocument();
    });

    it('shows correct confidence level for low confidence', () => {
      const section = createMockSection({ confidence: 'low' });
      render(<DocumentEditor {...defaultProps} sections={[section]} />);

      expect(screen.getByText('Low')).toBeInTheDocument();
    });
  });

  describe('generation controls', () => {
    it('renders regenerate button for each section', () => {
      render(<DocumentEditor {...defaultProps} sections={createMockSections(2)} />);

      const regenerateButtons = screen.getAllByRole('button', { name: 'Regenerate' });
      expect(regenerateButtons).toHaveLength(2);
    });

    it('calls onRegenerate with section id', () => {
      const onRegenerate = vi.fn();
      const section = createMockSection({ section_id: 'sec-123' });
      render(
        <DocumentEditor
          {...defaultProps}
          sections={[section]}
          onRegenerate={onRegenerate}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: 'Regenerate' }));

      expect(onRegenerate).toHaveBeenCalledWith('sec-123');
    });

    it('calls onAccept with section id', () => {
      const onAccept = vi.fn();
      const section = createMockSection({ section_id: 'sec-456' });
      render(
        <DocumentEditor
          {...defaultProps}
          sections={[section]}
          onAccept={onAccept}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: 'Accept' }));

      expect(onAccept).toHaveBeenCalledWith('sec-456');
    });
  });

  describe('regenerating state', () => {
    it('shows regenerating state for specific section', () => {
      const sections = createMockSections(2);
      render(
        <DocumentEditor
          {...defaultProps}
          sections={sections}
          regeneratingSection={sections[0].section_id}
        />
      );

      const buttons = screen.getAllByRole('button');
      const regeneratingButton = buttons.find((b) => b.textContent === 'Regenerating...');
      expect(regeneratingButton).toBeDefined();
    });

    it('hides edit button when section is regenerating', () => {
      const section = createMockSection({ section_id: 'sec-regen' });
      render(
        <DocumentEditor
          {...defaultProps}
          sections={[section]}
          regeneratingSection="sec-regen"
        />
      );

      expect(screen.queryByRole('button', { name: 'Edit section' })).not.toBeInTheDocument();
    });
  });

  describe('revert functionality', () => {
    it('shows revert button when section is edited and onRevert provided', () => {
      const section = createMockSection({ is_user_edited: true });
      render(
        <DocumentEditor
          {...defaultProps}
          sections={[section]}
          onRevert={vi.fn()}
        />
      );

      expect(screen.getByRole('button', { name: 'Revert Changes' })).toBeInTheDocument();
    });

    it('calls onRevert with section id', () => {
      const onRevert = vi.fn();
      const section = createMockSection({
        section_id: 'sec-revert',
        is_user_edited: true,
      });
      render(
        <DocumentEditor
          {...defaultProps}
          sections={[section]}
          onRevert={onRevert}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: 'Revert Changes' }));

      expect(onRevert).toHaveBeenCalledWith('sec-revert');
    });
  });

  describe('accessibility', () => {
    it('textareas have accessible labels', () => {
      const sections = createMockSections(2);
      render(<DocumentEditor {...defaultProps} sections={sections} />);

      expect(screen.getByLabelText('Content for section 1')).toBeInTheDocument();
      expect(screen.getByLabelText('Content for section 2')).toBeInTheDocument();
    });

    it('sections have aria-label', () => {
      const section = createMockSection();
      const { container } = render(<DocumentEditor {...defaultProps} sections={[section]} />);

      const sectionElement = container.querySelector('section.section-editor');
      expect(sectionElement).toHaveAttribute('aria-label', 'Section 1');
    });
  });

  describe('sidebar', () => {
    it('renders sidebar with sources', () => {
      const sources = createMockSources(3);
      const section = createMockSection({ sources });
      const { container } = render(<DocumentEditor {...defaultProps} sections={[section]} />);

      expect(screen.getByText('Sources')).toBeInTheDocument();
      // Scope to sidebar to avoid matching inline citations
      const sidebar = container.querySelector('.document-editor__sidebar') as HTMLElement;
      expect(within(sidebar).getByText('[Source 1]')).toBeInTheDocument();
      expect(within(sidebar).getByText('[Source 2]')).toBeInTheDocument();
      expect(within(sidebar).getByText('[Source 3]')).toBeInTheDocument();
    });
  });
});
