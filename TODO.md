# TODO

## Priority

### Updata readme and todo.md
- [X] too much irrelevant information in todo that should not be there. looks like it should have been in the readme.

### github
- [X] add description and topics to github repo, add licens


### create playground
- [ ] create playground for testing the app frontend

### check references cited
- [ ] check references cited, which authors are cited in the document

####--------------------####

### Test: v0.4.0 UX Improvements (needs manual verification)
- [ ] **Error boundary**: Trigger a React error — verify recovery screen appears with "Reload Application" button
- [ ] **Failed doc errors**: Upload a corrupt/invalid file — verify error message text shows on the document card
- [ ] **Retry (file)**: Fail a file document, click "Retry" — verify it reprocesses successfully
- [ ] **Retry (URL)**: Ingest a bad URL, click "Retry" after fixing — verify it reprocesses
- [ ] **Title editing**: In chat mode, hover a conversation — click pencil icon — edit title — press Enter — verify it persists after reload
- [ ] **Processing spinner**: Upload a document — verify spinning circle shows on the status badge while processing
- [ ] **Chat skeletons**: Switch to chat mode — verify skeleton placeholders show briefly before conversations load
- [ ] **Chat progress**: Send a chat message — verify spinner + stage messages + elapsed timer show while waiting

### UX Polish (Medium Effort)
- [X] Error toasts/notifications
- [X] Loading skeletons for chat history
- [X] Error boundary (crash recovery)
- [X] Failed document error messages
- [X] Document retry button
- [X] Conversation title editing
- [X] Processing spinner on document cards
- [X] Chat progress indicator (spinner + timer)
- [ ] Loading skeletons for document editor
- [ ] Drag to reorder document priority
- [ ] Document rename functionality
- [ ] Responsive design for tablet/mobile
- [ ] Syntax highlighting for code blocks in generated content

### High-Value Features (Worth the Investment)
- [X] **Chat mode** - Q&A conversation with documents (follow-up questions)
- [ ] **Source highlighting** - Click citation to highlight passage in original document
- [ ] **Custom prompt templates** - Save and reuse prompts (e.g., "Cover Letter", "Summary", "Analysis")
- [ ] **Generation history** - Save/recall previous generations with their sources
- [X] **Export to Word/PDF** - Formatted document export with citations

### Multi-Source Ingestion (Extends Document Types)
- [X] URL/webpage ingestion (fetch and extract text)
- [ ] YouTube transcript ingestion (via youtube-transcript-api)
- [ ] Markdown file support
- [ ] CSV/spreadsheet support (structured data)
- [ ] Image OCR (extract text from images/scanned PDFs)

### Organization & Management
- [ ] Projects/Workspaces (group documents into collections)
- [ ] Document tags/categories with filtering
- [ ] Full-text search across all documents
- [ ] Bulk document operations (delete multiple, export all)
- [ ] Document usage statistics (which docs cited most often)

### Advanced/Experimental Features
- [ ] **Comparison mode** - Compare information across multiple documents
- [ ] **Fact-check mode** - Verify generated claims against sources
- [ ] **Audio summary** - TTS podcast-style overview of documents
- [ ] **Collaborative editing** - Share generations with others
- [ ] **API access** - Expose generation as API for integrations
- [ ] **Fine-tuned retrieval** - Adjust similarity thresholds per query
- [ ] **Chunk visualization** - Visual map of document chunks and their relationships

### Technical Debt & Maintenance
- [ ] Add end-to-end tests (Playwright or Cypress)
- [X] Set up CI/CD pipeline
- [ ] Add request rate limiting
- [ ] Implement proper authentication (if multi-user)
- [ ] Database migration from JSON files to SQLite/PostgreSQL
- [ ] Docker containerization for deployment
