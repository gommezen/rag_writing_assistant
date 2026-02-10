# Custom Instructions for Programming & Development Project

## Project Context

This is a RAG writing assistant with a governance-first architecture. Code must support transparency, auditability, and user control over AI-generated content.

## Development Workflow

1. **Understand requirements** before writing code
2. **Propose alternatives** when trade-offs exist (e.g., FAISS vs managed vector DB)
3. **Get alignment** before implementing significant changes

## Project-Specific Standards

### RAG Pipeline Code
- Document retrieval thresholds and scoring logic
- Make chunking strategies explicit and configurable
- Log retrieval decisions for auditability
- Never silently drop sources or confidence metadata

### Frontend Components
- Preserve RAG metadata (sources, confidence, warnings) through the component tree
- Handle missing/partial data explicitly—show gaps, don't hide them
- Use TypeScript with strict mode for all React components

### Data Structures
Always include provenance in AI-generated content:
```python
@dataclass
class GeneratedSection:
    content: str
    sources: list[SourceReference]  # Never optional
    confidence: float | None        # None = unknown, not "high"
    warnings: list[str]
```

### Error Handling
- Surface errors to users with actionable messages
- Log errors with enough context to trace back to source documents
- Never swallow exceptions in retrieval or generation paths

### Testing After Refactors
- When modifying a service's internal API (renaming attributes, changing from direct assignment to cache/factory pattern), **immediately search for all test mocks targeting the old API** and update them
- Backend services use `_get_or_create_llm(model)` for LLM access — never mock `self._llm` directly; patch `_get_or_create_llm` instead
- Frontend components use `renderCitationsInText()` which splits text into React nodes — tests must account for text broken across elements
- `DocumentEditor` uses view/edit mode (click Edit → textarea → Save) — tests must follow this flow, not assume a textarea is always present

## Documentation Style
- Use Google-style docstrings for Python
- Comment the "why" for RAG-specific decisions (thresholds, chunking, prompt constraints)
- Document data flow between retrieval → generation → display

---

## Privacy & Data Handling

### Data Classification
- **Session-scoped**: Document content, embeddings, generation history (default: cleared on session end)
- **Persistent**: User preferences, document metadata (no content)
- **Never persist**: Raw document text in logs, PII in error messages

### Retention Rules
- Document vectors: Session-scoped by default, user-configurable retention
- Generation outputs: Ephemeral unless explicitly saved by user
- Audit logs: Structured, content-free (document_id, not document_text)

### Logging Constraints
- Never log document content to console in production
- Strip file paths and PII from error messages before logging
- Use structured audit format: `{action, document_id, timestamp, intent_type}`

### Secure Deletion
- When user deletes document: Remove from vector store, delete chunks, clear from any cache
- Deletion must be verifiable (not just dereferenced)

---

## Tech Stack
- **Backend**: Python with type hints
- **Frontend**: React with TypeScript (strict mode)
- **Styling**: Flexible (adapt to established patterns)
