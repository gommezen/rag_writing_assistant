# RAG Writing Assistant

Generate AI-written content grounded in your own documents, with full source transparency.

## Features

- **Document upload** - PDF, DOCX, and TXT with drag-and-drop support
- **Grounded generation** - AI content derived from your uploaded materials
- **Source citations** - Every claim traced back to retrieved documents
- **Confidence indicators** - Visual cues for high/medium/low confidence content
- **Section-level editing** - Regenerate or manually edit individual sections
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

# Retrieval settings
SIMILARITY_THRESHOLD=0.35
TOP_K=10

# Ollama connection
OLLAMA_BASE_URL=http://localhost:11434
```

### Alternative Models

| Model | Use Case | Notes |
|-------|----------|-------|
| `qwen2.5:7b-instruct-q4_0` | Generation (default) | Good prose quality, fast |
| `llama3.1:8b-instruct-q5_K_M` | Generation | Better reasoning, needs more RAM |
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
| `/api/documents` | POST | Upload document |
| `/api/documents` | GET | List documents |
| `/api/documents/{id}` | GET | Get document |
| `/api/documents/{id}` | DELETE | Delete document |
| `/api/generate` | POST | Generate draft |
| `/api/generate/section` | POST | Regenerate section |
| `/api/health` | GET | Health check |

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
