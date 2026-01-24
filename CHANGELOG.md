# Changelog

All notable changes to this project will be documented in this file.

## [0.2.2] - 2026-01-24

### Added

#### Chat Persistence & History
- **Conversation Storage**: Conversations now persist across server restarts
  - JSON file-based storage in `data/conversations/`
  - Lightweight index file for fast listing
  - Individual files per conversation for full data
  - Auto-save after each message

- **Conversation History UI**: New sidebar component in chat mode
  - Browse past conversations with title and timestamp
  - Resume any previous conversation
  - Delete conversations with confirmation
  - "New Chat" button to start fresh
  - Highlights current active conversation

- **Backend Endpoints**:
  - `GET /api/chat` - List all conversations (sorted by updated_at)
  - `DELETE /api/chat/{id}` - Delete a conversation
  - `PATCH /api/chat/{id}` - Update conversation title

- **New Models**:
  - `ConversationSummary` - Lightweight summary for listings
  - `ConversationSummaryResponse` - API response model
  - `from_dict()` methods on `ChatMessage` and `Conversation` for deserialization

- **New Services**:
  - `ConversationStore` - File-based persistence service
  - Methods: `save_conversation`, `load_conversation`, `list_conversations`, `delete_conversation`, `update_title`

#### Frontend
- `ConversationHistory` component with delete confirmation
- `useConversations` hook for listing conversations
- `useDeleteConversation` hook with cache invalidation
- `useUpdateConversationTitle` hook
- API client methods for conversation management

### Changed
- `ChatService` now uses `ConversationStore` for persistence
- Conversations loaded from storage on server startup
- Chat mode sidebar shows conversation history instead of just "New Chat" button

---

## [0.2.1] - 2026-01-24

### Added

#### Frontend
- **Coverage Stats Display**: New UI component showing document coverage after generation
  - Coverage percentage with color-coded indicator (green ≥40%, yellow 20-40%, red <20%)
  - Chunks analyzed vs total chunks
  - Retrieval type (diverse/similarity)
  - Intent mode badge (ANALYSIS/QA/WRITING)
  - Blind spots list (if any regions weren't covered)

- **Expand Coverage Button**: "↑ Expand to ~50%" button in coverage stats
  - Only appears when coverage <50% and using diverse retrieval
  - Triggers `escalate_coverage` parameter for deeper analysis
  - Re-generates with 15% additional coverage

#### Backend
- **Coverage-Based Retrieval**: Diverse retrieval now targets coverage percentage instead of fixed chunk count
  - `target_coverage_pct` parameter (default: 35%)
  - Dynamically calculates chunks needed based on document size
  - Escalation adds 15% coverage (up to 60% max)

- **Intent-Specific Model Selection**: Generation uses different models per intent
  - ANALYSIS: `llama3.1:8b-instruct-q8_0` (higher quality reasoning)
  - WRITING: `qwen2.5:7b-instruct-q4_0` (good prose quality)
  - QA: `gemma3:4b` (fast responses)

- **Improved Intent Detection**: Better pattern matching for summary requests
  - "write a summary" now correctly triggers ANALYSIS mode (not WRITING)
  - "of this document" triggers ANALYSIS mode
  - ANALYSIS patterns checked before WRITING to prevent false matches
  - Higher confidence boost for ANALYSIS (0.20 vs 0.15)

#### Configuration
- `DEFAULT_COVERAGE_PCT`: Target coverage for diverse retrieval (default: 35%)
- `MAX_COVERAGE_PCT`: Maximum coverage with escalation (default: 60%)
- `ANALYSIS_MODEL`, `WRITING_MODEL`, `QA_MODEL`: Intent-specific model overrides

### Changed
- Diverse retrieval now uses percentage-based targeting instead of fixed 30 chunks
- Intent detection order changed: ANALYSIS → QA → WRITING (was WRITING first)
- Frontend types updated with full coverage and intent type definitions

---

## [0.2.0] - 2026-01-24

### Added

#### Document Intelligence System
- **Intent Detection Service**: Automatically classifies queries as ANALYSIS, QA, or WRITING based on pattern matching
  - ANALYSIS: "summarize", "overview", "main points", "key takeaways"
  - QA: Questions starting with what/when/where/who/why/how
  - WRITING: "write", "draft", "create", "compose" (default for ambiguous queries)

- **Diverse Retrieval Service**: Region-based sampling for analysis mode
  - Samples from intro (30%), middle (40%), and conclusion (30%) regions
  - Provides representative coverage across entire document
  - Target: ~30 chunks per document

- **Coverage Descriptor**: Tracks what portion of documents the system has seen
  - `chunks_seen` / `chunks_total` with percentage
  - `regions_covered` and `regions_missing`
  - `blind_spots` list for transparency
  - `coverage_summary` injected into prompts

- **Summary Scope Detection**: Distinguishes broad from focused summaries
  - BROAD: "Summarize this document" → exploratory overview + suggested focus areas
  - FOCUSED: "Summarize the ethics section" → deep synthesis on specific topic
  - Enables escalation flow: broad overview → user picks focus → deep dive

- **Epistemic Guardrails in Prompts**:
  - Coverage-aware system prompts ("You are seeing ~12% of the document...")
  - Claim-evidence separation (Observations vs Synthesized Patterns)
  - Contradiction awareness (present both views without forcing resolution)
  - Blind spots section (what couldn't be assessed)
  - Questions raised section (intellectual honesty)

#### New Prompt Templates
- `ANALYSIS_SYSTEM_PROMPT`: Epistemic rules for document analysis
- `ANALYSIS_PROMPT`: Structured output with 5 sections
- `EXPLORATORY_SUMMARY_PROMPT`: Overview + suggested focus areas
- `FOCUSED_SUMMARY_PROMPT`: Deep synthesis on specific topic
- `COVERAGE_AWARE_GENERATION_PROMPT`: Writing/QA with coverage context

#### New Models
- `QueryIntent` enum (ANALYSIS, QA, WRITING)
- `RetrievalType` enum (SIMILARITY, DIVERSE)
- `DocumentRegion` enum (INTRO, MIDDLE, CONCLUSION)
- `SummaryScope` enum (BROAD, FOCUSED, NOT_APPLICABLE)
- `DocumentCoverage` dataclass
- `CoverageDescriptor` dataclass
- `IntentClassification` dataclass

#### Tests
- 62 new tests for intent detection and summary scope
- Tests for diverse retrieval and coverage computation

### Changed

#### Backend
- Generation service now detects intent and routes to appropriate retrieval strategy
- Analysis queries use diverse sampling; writing/QA use similarity search
- Prompts include coverage context so LLM knows its limitations
- `RetrievalMetadata` extended with `coverage` and `intent` fields

---

## [0.1.2] - 2026-01-24

### Added

#### Backend
- **Non-blocking document upload**: Upload endpoint returns immediately with `pending` status while processing happens in background
- **Background processing**: Document parsing, chunking, and embedding now run asynchronously using ThreadPoolExecutor
- **Stale document cleanup**: Documents stuck in `processing` or `pending` state are marked as `failed` on server restart

#### Frontend
- **Document polling**: Frontend automatically polls for document status until processing completes
- **Processing animation**: Documents show pulsing animation while in `pending` or `processing` state
- **Polling timeout**: Stops polling after ~2 minutes to prevent infinite loops

### Changed

#### Backend
- `POST /api/documents` now returns immediately with `pending` status instead of waiting for full processing
- Document status lifecycle: `pending` → `processing` → `ready` (or `failed`)

#### Frontend
- `useUploadDocument` hook now tracks uploaded document ID for polling
- Documents list refreshes automatically when processing completes

---

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
