/**
 * Tests for SourceCard component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SourceCard } from './SourceCard';
import { createMockSource } from '../../test/mocks';

describe('SourceCard', () => {
  it('renders source index and relevance score', () => {
    const source = createMockSource({ relevance_score: 0.85 });

    render(<SourceCard source={source} index={1} />);

    expect(screen.getByText('[Source 1]')).toBeInTheDocument();
    expect(screen.getByText('85% match')).toBeInTheDocument();
  });

  it('renders document title from metadata', () => {
    const source = createMockSource({
      metadata: { title: 'My Document Title', filename: 'doc.pdf' },
    });

    render(<SourceCard source={source} index={1} />);

    expect(screen.getByText('My Document Title')).toBeInTheDocument();
  });

  it('renders excerpt content', () => {
    const source = createMockSource({
      excerpt: 'This is the important excerpt text.',
    });

    render(<SourceCard source={source} index={1} />);

    expect(screen.getByText('This is the important excerpt text.')).toBeInTheDocument();
  });

  it('renders Untitled when title is missing', () => {
    const source = createMockSource({
      metadata: {},
    });

    render(<SourceCard source={source} index={1} />);

    expect(screen.getByText('Untitled')).toBeInTheDocument();
  });

  it('handles click when onClick provided', () => {
    const source = createMockSource();
    const handleClick = vi.fn();

    render(<SourceCard source={source} index={1} onClick={handleClick} />);

    const card = screen.getByRole('button');
    fireEvent.click(card);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('handles keyboard interaction with Enter key', () => {
    const source = createMockSource();
    const handleClick = vi.fn();

    render(<SourceCard source={source} index={1} onClick={handleClick} />);

    const card = screen.getByRole('button');
    fireEvent.keyDown(card, { key: 'Enter' });

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('handles keyboard interaction with Space key', () => {
    const source = createMockSource();
    const handleClick = vi.fn();

    render(<SourceCard source={source} index={1} onClick={handleClick} />);

    const card = screen.getByRole('button');
    fireEvent.keyDown(card, { key: ' ' });

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('does not have button role when onClick is not provided', () => {
    const source = createMockSource();

    render(<SourceCard source={source} index={1} />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('displays filename metadata when available', () => {
    const source = createMockSource({
      metadata: { title: 'Test', filename: 'important_doc.pdf' },
    });

    render(<SourceCard source={source} index={1} />);

    expect(screen.getByText('important_doc.pdf')).toBeInTheDocument();
  });

  it('applies highlighted class when isHighlighted is true', () => {
    const source = createMockSource();

    const { container } = render(
      <SourceCard source={source} index={1} isHighlighted={true} />
    );

    expect(container.firstChild).toHaveClass('source-card--highlighted');
  });

  it('does not apply highlighted class when isHighlighted is false', () => {
    const source = createMockSource();

    const { container } = render(
      <SourceCard source={source} index={1} isHighlighted={false} />
    );

    expect(container.firstChild).not.toHaveClass('source-card--highlighted');
  });

  it('renders relevance score with correct precision in title', () => {
    const source = createMockSource({ relevance_score: 0.8567 });

    render(<SourceCard source={source} index={1} />);

    const relevanceElement = screen.getByTitle('Relevance score: 0.857');
    expect(relevanceElement).toBeInTheDocument();
  });
});
