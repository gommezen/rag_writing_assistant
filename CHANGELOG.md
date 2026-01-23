# Changelog

All notable changes to this project will be documented in this file.

## [0.1.1] - 2026-01-23

### Added

#### Frontend
- **Dark mode**: Toggle between light and dark themes with system preference detection and localStorage persistence
- **Drag and drop file upload**: Files can now be uploaded by dragging and dropping onto the upload area
- **Accept button visual feedback**: Shows "Accepted!" badge and green border animation when section is accepted

### Fixed

#### Backend
- **Invalid source citations**: LLM now explicitly told available source count; invalid citations (e.g., [Source 15] when only 10 sources exist) are automatically removed
- **Confidence level detection**: Fixed prompt to mandate inline citations with examples, preventing "Unknown" confidence when LLM omitted citations
- **Regenerate section API**: Fixed endpoint to properly accept `original_content` and `refinement_prompt` parameters
- **Deprecated datetime.utcnow()**: Replaced with timezone-aware `datetime.now(UTC)` for Python 3.12+ compatibility
- **Health endpoint typing**: Now returns properly typed `HealthResponse` model

#### Frontend
- **Document card visibility**: Improved text contrast and added border for better readability in sidebar
- **Warning banner formatting**: Only strips snake_case prefixes, preserving messages with colons in content
- **Source sidebar selection**: Sources now correctly update when selecting different sections or after new generation

### Changed

#### Backend
- **Confidence calculation**: Now based on absolute citation count per section (3+ = HIGH, 1-2 = MEDIUM, 0 = UNKNOWN) instead of ratio against all sources
- **Generation model**: Default changed to `qwen2.5:7b-instruct-q4_0` for improved prose quality (configurable via `GENERATION_MODEL` env var)

---

## [0.1.0] - 2026-01-22

### Added

#### Backend
- FastAPI application with CORS middleware
- Document ingestion service supporting PDF, DOCX, and TXT files
- FAISS vector store with add, search, delete, and persistence
- Retrieval service with similarity threshold and top-k filtering
- Generation service with Ollama LLM integration
- Validation service for warnings and confidence assessment
- API endpoints:
  - `POST /api/documents` - Upload document
  - `GET /api/documents` - List documents
  - `GET /api/documents/{id}` - Get document
  - `DELETE /api/documents/{id}` - Delete document
  - `POST /api/generate` - Generate draft
  - `POST /api/generate/section` - Regenerate section
  - `GET /api/health` - Health check
- Comprehensive test suite (115 tests)
- Pydantic models for all data structures

#### Frontend
- React application with TypeScript (strict mode)
- React Query for server state management
- Components:
  - `DocumentEditor` - Main editor with section editing
  - `SourceCard` - Display retrieved sources with relevance scores
  - `ConfidenceIndicator` - Visual confidence levels (high/medium/low/unknown)
  - `WarningBanner` - Alert display for warnings
  - `GenerationControls` - Regenerate/Accept/Revert buttons
- API client with error handling
- Custom hooks: `useDocuments`, `useGeneration`
- Professional CSS styling with CSS custom properties
- Comprehensive test suite (104 tests)

#### Configuration
- Ollama integration configured:
  - Embedding model: `mxbai-embed-large`
  - Generation model: configurable (default: `qwen2.5:7b-instruct-q4_0`)
- Environment-based configuration via pydantic-settings
- Configurable similarity threshold via `SIMILARITY_THRESHOLD` env var
- TypeScript strict mode with test files excluded from build

#### Documentation
- README.md with setup instructions
- TODO.md with project status and next steps
- .gitignore for Python, Node.js, and project-specific files

### Technical Details
- Backend: Python 3.11+, FastAPI, LangChain, FAISS
- Frontend: React 18, TypeScript, Vite, Vitest
- Total tests: 219 (115 backend + 104 frontend)

### Current Limitations
- **No document categorization**: All documents treated as generic source material
- **No targeted retrieval**: Cannot specify "use this job advert + my past applications"
- **No use-case workflows**: No specialized flows for job applications, reports, etc.

### How RAG Works (Clarification)
RAG does NOT learn or train on user documents. The system:
1. Chunks and indexes documents as vectors
2. At query time, finds chunks most similar to the prompt
3. Passes retrieved chunks to LLM as context
4. LLM generates content grounded in those sources

The system *retrieves and references* your writing—it doesn't *learn your style*.
