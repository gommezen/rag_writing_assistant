# RAG Writing Assistant

A governance-first RAG (Retrieval-Augmented Generation) writing assistant. The system emphasizes transparency, auditability, and user control over AI-generated content.

## What is RAG?

**RAG (Retrieval-Augmented Generation)** does NOT learn or train on your documents. Instead:

1. **Upload**: Your documents are chunked and converted to vectors (mathematical representations)
2. **Query**: When you generate, your prompt searches for similar chunks
3. **Generate**: The LLM receives your prompt + retrieved chunks, producing grounded content with citations

**Key distinction**: The system *retrieves and references* your writing—it doesn't *learn your style*.

### Benefits over plain LLM generation

| Without RAG                                      | With RAG                                          |
| ------------------------------------------------ | ------------------------------------------------- |
| Model may invent details when context is missing | Model grounds output in retrieved documents       |
| No explicit source grounding                     | Claims can be traced to retrieved sources         |
| Output confidence is implicit                    | Uncertainty and gaps can be surfaced explicitly   |
| Generic phrasing based on training data          | Content derived from *your* materials and context |

## Architecture

- **Backend**: Python/FastAPI with FAISS vector store and Ollama for LLM
- **Frontend**: React/TypeScript with React Query

## Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.ai/) running locally

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Testing

### Backend (115 tests)

```bash
cd backend
pytest tests/ -v
```

### Frontend (104 tests)

```bash
cd frontend
npm run test
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/routes/      # API endpoints
│   │   ├── models/          # Pydantic models
│   │   ├── rag/             # Vector store, embeddings, chunking
│   │   └── services/        # Business logic
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── api/             # API client
│   │   ├── components/      # React components
│   │   ├── hooks/           # React Query hooks
│   │   └── types/           # TypeScript types
│   └── src/test/
```

## Configuration

Create `backend/.env` to customize settings:

```env
# LLM Models (must be available in Ollama)
GENERATION_MODEL=qwen2.5:7b-instruct-q4_0
EMBEDDING_MODEL=mxbai-embed-large

# Retrieval settings
SIMILARITY_THRESHOLD=0.35
TOP_K=10

# Ollama connection
OLLAMA_BASE_URL=http://localhost:11434
```

### Recommended Models

| Model | Use Case | Notes |
|-------|----------|-------|
| `qwen2.5:7b-instruct-q4_0` | Generation (default) | Good prose quality, fast |
| `llama3.1:8b-instruct-q5_K_M` | Generation | Better reasoning, needs more RAM |
| `mxbai-embed-large` | Embeddings (default) | High quality retrieval |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/documents` | POST | Upload document |
| `/api/documents` | GET | List documents |
| `/api/documents/{id}` | GET | Get document |
| `/api/documents/{id}` | DELETE | Delete document |
| `/api/generate` | POST | Generate draft |
| `/api/generate/section` | POST | Regenerate section |
| `/api/health` | GET | Health check |

## License

MIT
