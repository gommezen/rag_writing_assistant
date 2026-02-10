# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A governance-first RAG (Retrieval-Augmented Generation) document intelligence platform designed for enterprise internal use. The system emphasizes transparency, auditability, and user control over AI-generated content.

**Core Philosophy**: If users cannot explain why the AI produced something, the system has failed.

## How RAG Works (Not Learning)

RAG (Retrieval-Augmented Generation) does **not** train or learn from user documents. The flow is:

```
UPLOAD → Documents chunked → Converted to vectors (for similarity search)
           ↓
QUERY  → Prompt converted to vector → Finds most similar chunks
           ↓
GENERATE → LLM receives: prompt + retrieved chunks → Generates grounded content
```

**Key points**:
- Strictly retrieval-based (no training/fine-tuning on user data)
- System *retrieves and quotes* existing writing as context
- All outputs grounded in retrieved content with citations
- User sees exactly which sources were used

## Current Implementation Status

**Implemented (v0.2.1)**:

*Core Features*:
- Generic document upload (PDF, DOCX, TXT) with drag-and-drop
- Vector store indexing with FAISS
- LLM generation with mandatory source citations
- Confidence indicators (high/medium/low) and warnings
- Section-level editing and regeneration
- Citation sanitization (removes invalid source references)

*Document Intelligence System*:
- **Intent Detection**: Queries classified as ANALYSIS, QA, or WRITING
- **Intent-Specific Models**: Different LLMs selected per intent (analysis/writing/QA)
- **Diverse Retrieval**: Region-based sampling (intro/middle/conclusion) for analysis
- **Coverage-Based Targeting**: Retrieves ~35% of document by default (configurable)
- **Coverage Awareness**: System tracks and reports what portion of documents it has seen
- **Coverage Display UI**: Shows % coverage, chunks analyzed, retrieval type, intent mode
- **Coverage Escalation UI**: "Expand to ~50%" button for deeper analysis
- **Epistemic Guardrails**: LLM confidence calibrated to actual coverage
- **Summary Scope**: Broad overviews vs focused topic analysis
- **Structured Analysis Output**: Observations, Patterns, Contradictions, Questions, Blind Spots

*How Intent Routing Works*:
```
Query: "Summarize this document"
  → Intent: ANALYSIS
  → Retrieval: DIVERSE (samples from all regions)
  → Coverage: ~35% (110 of 322 chunks)
  → Scope: BROAD
  → Output: Exploratory overview + suggested focus areas

Query: "Write a summary about X"
  → Intent: ANALYSIS (not WRITING - "summary" takes priority)
  → Retrieval: DIVERSE
  → Coverage: ~35%
  → Output: Summary with coverage transparency

Query: "What is data feminism?"
  → Intent: QA
  → Retrieval: SIMILARITY (top-k matches)
  → Output: Direct answer with citations

Query: "Write a report about X"
  → Intent: WRITING
  → Retrieval: SIMILARITY (existing behavior)
  → Output: Generated content with citations
```

**Not Yet Implemented**:
- Document categorization (e.g., "job advert" vs "reference material")
- Targeted retrieval by document type
- Chat mode (follow-up questions in conversation)

## Architecture

### Governance Model

The project uses specialized Claude Code agent roles (in `.claude/commands/`):

1. **RAG & Governance Architect** (`/rag_governance_architect`) - Reviews RAG design, prompts, and data handling. Operates as reviewer/challenger, not primary implementer.

2. **Frontend Enablement Agent** (`/frontend_enablement_agent`) - Designs transparent, inspectable UIs that make AI behavior understandable. Design authority for frontend.

3. **UI Component Agent** (`/ui-component`) - Generates React component implementations. Subordinate to Frontend Enablement Agent.

4. **Project Instructions** (`/project_instructions`) - Project-specific coding standards for RAG pipeline, components, and data structures.

### Design Principles

**RAG System**:
- Strictly retrieval-based (no training/fine-tuning on user data)
- All outputs must be grounded in retrieved content
- Explicit flagging of hallucination risks
- Personal documents treated as high-risk assets

**Frontend**:
- Transparency over automation (sources visible by default)
- Control over magic (users can regenerate, edit all content)
- Calm, professional interface (enterprise-suitable)

### Implemented Components

- `DocumentEditor` - Document-style editor distinguishing AI-generated from user content
- `SourceCard` - RAG explainability display showing retrieved sources with relevance scores
- `WarningBanner` - Neutral guidance for unsupported claims, tone mismatches
- `GenerationControls` - Section-level regeneration with accept/revert controls
- `ConfidenceIndicator` - Visual confidence levels (high/medium/low/unknown)

## Technology Stack

- **Backend**: Python 3.11+ with type hints, FastAPI, Pydantic
- **Frontend**: React 18 with TypeScript (strict mode), React Query
- **Vector Database**: FAISS (local, file-based persistence)
- **LLM Orchestration**: LangChain with Ollama
- **Embedding Model**: mxbai-embed-large
- **Generation Model**: qwen2.5:7b-instruct-q4_0

## Coding Standards

- Never silently drop sources or confidence metadata in RAG pipeline
- Preserve RAG metadata (sources, confidence, warnings) through frontend component tree
- Handle missing/partial data explicitly—show gaps, don't hide them
- Document retrieval thresholds, chunking strategies, and prompt constraints

## CI & Testing Rules

### Tool Version Pinning
- **Pin exact versions** for linters/formatters in both `requirements.txt` and `.pre-commit-config.yaml`
- Pre-commit hooks run from the **repo root**; CI runs from `backend/` or `frontend/`. This affects import classification — always set `known-first-party` in ruff isort config
- After changing linter versions, run checks locally from both the repo root AND the subdirectory to verify consistency

### Test Mock Hygiene
- **Mock at the interface, not the attribute**: When mocking service internals, patch the method that creates/returns the dependency (e.g., `_get_or_create_llm`), not an internal attribute (e.g., `self._llm`). Internal attributes change during refactors; method interfaces are more stable
- **Verify mocks are actually used**: If a test patches something and the service still hits external services (503 errors, connection failures), the mock is targeting the wrong thing
- When refactoring a service's internal API (e.g., replacing `self._llm` with `self._llm_cache`), search for all test files that mock that attribute and update them

### Frontend Test Patterns
- When components render content as both inline elements AND sidebar elements (e.g., citations appear in content AND source cards), use `within(container.querySelector('.sidebar'))` to scope queries
- After refactoring from always-editable (textarea) to view/edit modes, update tests to follow the edit flow: click Edit → interact with textarea → click Save
- When `renderCitationsInText` splits plain text into React nodes, `getByText(fullString)` will fail — use container queries or partial matchers instead

## Agent Collaboration Rules

- Frontend agent must not modify backend contracts without approval
- UI Component agent implements designs from Frontend Enablement Agent
- RAG architect reviews all retrieval/prompt changes
- Prefer simple, auditable solutions over complex ones
- Escalate unclear requirements rather than guessing
