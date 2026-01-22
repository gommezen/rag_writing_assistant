/**
 * Re-export all hooks from a single entry point.
 */

export {
  useDeleteDocument,
  useDocument,
  useDocuments,
  useUploadDocument,
} from './useDocuments';

export { useGenerateDraft, useRegenerateSection } from './useGeneration';
