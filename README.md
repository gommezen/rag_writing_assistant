# RAG Writing Assistant

Generate AI-written content grounded in your own documents, with full source transparency.

## Features

- **Document upload** - PDF, DOCX, and TXT with drag-and-drop support (non-blocking)
- **Grounded generation** - AI content derived from your uploaded materials
- **Source citations** - Every claim traced back to retrieved documents
- **Confidence indicators** - Visual cues for high/medium/low confidence content
- **Section-level editing** - Regenerate or manually edit individual sections
- **Coverage transparency** - See exactly what % of your documents were analyzed
- **Intent detection** - Auto-selects best model and retrieval strategy per query
- **Chat mode** - Multi-turn conversations with persistent history
- **Conversation history** - Resume past chats, browse history in sidebar
- **Fully local** - Documents never leave your machine (runs on Ollama)

## Governance & Transparency

### No Learning From Your Data

RAG does **not** train on your documents. Your files are chunked and indexed for retrieval only—the AI model is never modified. Deleting a document removes it completely.

### Citation Enforcement

Every paragraph must cite sources using `[Source N]` notation. Citations are validated post-generation and mapped back to actual document chunks.

### Coverage Tracking

The system reports what % of your documents it actually analyzed:

- **~8-10%**: Similarity search (Q&A, specific questions)
- **~35%**: Diverse sampling (summaries, analysis)
- **~50-60%**: Expanded coverage (deep analysis)

A summary based on 8% is different from 35%—the UI shows this with color-coded indicators and an "Expand coverage" option.

### Confidence Levels

| Level | Criteria |
|-------|----------|
| HIGH | 3+ citations |
| MEDIUM | 1-2 citations |
| LOW | Hedging language detected |
| UNKNOWN | 0 citations |

### Blind Spot Detection

The system reports what it **didn't** see—documents with no coverage, regions (intro/middle/conclusion) that weren't sampled. This prevents false confidence from partial reads.

## Quick Start

1. **Install Ollama** from [ollama.ai](https://ollama.ai/)

2. **Pull required models**:
   ```bash
   ollama pull qwen2.5:7b-instruct-q4_0
   ollama pull mxbai-embed-large
   ```

3. **Start the backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

4. **Start the frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Open** http://localhost:5173 in your browser

## Requirements

- Python 3.11+
- Node.js 18+
- Ollama running locally

## Configuration

Create `backend/.env` to customize:

```env
# LLM Models (must be available in Ollama)
GENERATION_MODEL=qwen2.5:7b-instruct-q4_0
EMBEDDING_MODEL=mxbai-embed-large

# Intent-specific models (optional - uses GENERATION_MODEL as fallback)
ANALYSIS_MODEL=llama3.1:8b-instruct-q8_0   # Deep analysis, summaries
WRITING_MODEL=qwen2.5:7b-instruct-q4_0     # Content generation
QA_MODEL=gemma3:4b                          # Quick Q&A responses

# Retrieval settings
SIMILARITY_THRESHOLD=0.35
TOP_K=10

# Coverage settings (for analysis/summary mode)
DEFAULT_COVERAGE_PCT=35                 # Target coverage for summaries
MAX_COVERAGE_PCT=60                     # Max coverage with escalation

# Ollama connection
OLLAMA_BASE_URL=http://localhost:11434
```

### Intent Detection & Coverage

The system automatically detects query intent and adjusts behavior:

| Query Type | Intent | Retrieval | Coverage |
|------------|--------|-----------|----------|
| "Summarize this document" | ANALYSIS | Diverse (regions) | ~35% |
| "Write a summary about X" | ANALYSIS | Diverse (regions) | ~35% |
| "What is data feminism?" | QA | Similarity | Top-k matches |
| "Write a report on X" | WRITING | Similarity | Top-k matches |

**Coverage Display**: After generation, the UI shows:
- Coverage percentage with color indicator (green ≥40%, yellow 20-40%, red <20%)
- Chunks analyzed vs total chunks
- Retrieval type (diverse/similarity)
- Intent mode (ANALYSIS/QA/WRITING)
- "Expand to ~50%" button for deeper analysis

### Chat Mode

Switch to Chat mode for multi-turn conversations about your documents:

- **Follow-up questions**: Ask clarifying questions that build on prior context
- **Conversation history**: Browse and resume past conversations in the sidebar
- **Persistent storage**: Conversations survive server restarts (stored in `data/conversations/`)
- **Per-message sources**: Each response shows which document chunks were used
- **Cumulative coverage**: Track total document coverage across a conversation

Chat history is stored locally as JSON files and is never sent externally.

### Intent-Specific Models

The system automatically selects the best model based on query intent:

| Intent | Default Model | Use Case |
|--------|---------------|----------|
| Analysis | `llama3.1:8b-instruct-q8_0` | Summaries, deep analysis |
| Writing | `qwen2.5:7b-instruct-q4_0` | Content generation, reports |
| Q&A | `gemma3:4b` | Quick factual questions |

### Alternative Models

| Model | Use Case | Notes |
|-------|----------|-------|
| `qwen2.5:7b-instruct-q4_0` | Generation (default) | Good prose quality, fast |
| `llama3.1:8b-instruct-q8_0` | Analysis | Higher quality reasoning |
| `gemma3:4b` | Q&A | Very fast for simple queries |
| `mxbai-embed-large` | Embeddings (default) | High quality retrieval |

## Project Structure

```
backend/
├── app/
│   ├── api/routes/      # API endpoints
│   ├── models/          # Pydantic models
│   ├── rag/             # Vector store, embeddings, chunking
│   └── services/        # Business logic
└── tests/

frontend/
├── src/
│   ├── api/             # API client
│   ├── components/      # React components
│   ├── hooks/           # React Query hooks
│   └── types/           # TypeScript types
└── src/test/
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/documents` | POST | Upload document (returns immediately, poll for status) |
| `/api/documents` | GET | List documents |
| `/api/documents/{id}` | GET | Get document (use for polling status) |
| `/api/documents/{id}` | DELETE | Delete document |
| `/api/generate` | POST | Generate draft |
| `/api/generate/section` | POST | Regenerate section |
| `/api/chat` | POST | Send chat message (creates or continues conversation) |
| `/api/chat` | GET | List all conversations |
| `/api/chat/{id}` | GET | Get conversation by ID |
| `/api/chat/{id}` | DELETE | Delete conversation |
| `/api/chat/{id}` | PATCH | Update conversation title |
| `/api/health` | GET | Health check |

### Document Upload Flow

Uploads are non-blocking. The endpoint returns immediately with `status: "pending"`:

```bash
# 1. Upload returns immediately
curl -X POST http://localhost:8000/api/documents -F "file=@document.pdf"
# Response: {"document_id": "abc123", "status": "pending", ...}

# 2. Poll for completion
curl http://localhost:8000/api/documents/abc123
# Response: {"status": "processing", ...} then {"status": "ready", ...}
```

Status lifecycle: `pending` → `processing` → `ready` (or `failed`)

## Development

### Run tests

```bash
# Backend (pytest)
cd backend && pytest tests/ -v

# Frontend (vitest)
cd frontend && npm run test
```

### Architecture

- **Backend**: Python/FastAPI with FAISS vector store
- **Frontend**: React/TypeScript with React Query

## License

MIT
