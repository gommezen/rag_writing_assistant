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
- **Fully local** - Documents never leave your machine (runs on Ollama)

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
