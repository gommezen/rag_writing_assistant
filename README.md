# RAG Writing Assistant

A governance-first RAG (Retrieval-Augmented Generation) writing assistant. The system emphasizes transparency, auditability, and user control over AI-generated content.

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
