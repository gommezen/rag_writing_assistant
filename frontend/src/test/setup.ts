import '@testing-library/jest-dom';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup after each test
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// Global fetch mock
global.fetch = vi.fn();

// Reset fetch mock before each test
beforeEach(() => {
  (global.fetch as ReturnType<typeof vi.fn>).mockReset();
});
