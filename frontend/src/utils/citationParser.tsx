/**
 * citationParser - parses text containing [Source N] citations
 * and returns React nodes with interactive Citation components.
 *
 * This utility supports the governance principle of making AI behavior
 * understandable by transforming plain-text citations into clickable
 * elements that reveal their source context.
 */

import type { ReactNode } from 'react';
import { Citation } from '../components/Citation';
import type { SourceReference } from '../types';

/** Regex to match [Source N] patterns where N is a positive integer */
const CITATION_REGEX = /\[Source (\d+)\]/g;

/**
 * Renders text content with interactive Citation components.
 *
 * @param text - The text content potentially containing [Source N] citations
 * @param sources - Array of source references (1-indexed access: sources[0] = Source 1)
 * @param onCitationClick - Callback when a citation is clicked
 * @returns Array of text nodes and Citation components
 *
 * @example
 * const content = renderCitationsInText(
 *   "According to [Source 1], the data shows [Source 2].",
 *   sources,
 *   (idx) => scrollToSource(idx)
 * );
 * // Returns: ["According to ", <Citation index={1} />, ", the data shows ", <Citation index={2} />, "."]
 */
export function renderCitationsInText(
  text: string,
  sources: SourceReference[],
  onCitationClick?: (index: number) => void
): ReactNode[] {
  const result: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let keyCounter = 0;

  // Reset regex state
  CITATION_REGEX.lastIndex = 0;

  while ((match = CITATION_REGEX.exec(text)) !== null) {
    const fullMatch = match[0];
    const indexStr = match[1];

    // Skip if no valid capture group
    if (!indexStr) continue;

    const citationIndex = parseInt(indexStr, 10);

    // Add text before the citation
    if (match.index > lastIndex) {
      result.push(text.substring(lastIndex, match.index));
    }

    // Get source for this citation (1-indexed, so sources[0] = Source 1)
    const source = sources[citationIndex - 1];

    result.push(
      <Citation
        key={`citation-${keyCounter++}`}
        index={citationIndex}
        source={source}
        {...(onCitationClick ? { onActivate: onCitationClick } : {})}
      />
    );

    lastIndex = match.index + fullMatch.length;
  }

  // Add remaining text after last citation
  if (lastIndex < text.length) {
    result.push(text.substring(lastIndex));
  }

  // If no citations found, return original text as single element
  if (result.length === 0) {
    return [text];
  }

  return result;
}

/**
 * Checks if text contains any [Source N] citations.
 *
 * @param text - The text to check
 * @returns true if citations are present
 */
export function hasCitations(text: string): boolean {
  CITATION_REGEX.lastIndex = 0;
  return CITATION_REGEX.test(text);
}

/**
 * Extracts all citation indices from text.
 *
 * @param text - The text to parse
 * @returns Array of citation indices (1-based)
 */
export function extractCitationIndices(text: string): number[] {
  const indices: number[] = [];
  let match: RegExpExecArray | null;

  CITATION_REGEX.lastIndex = 0;

  while ((match = CITATION_REGEX.exec(text)) !== null) {
    const indexStr = match[1];
    if (!indexStr) continue;

    const index = parseInt(indexStr, 10);
    if (!indices.includes(index)) {
      indices.push(index);
    }
  }

  return indices.sort((a, b) => a - b);
}
