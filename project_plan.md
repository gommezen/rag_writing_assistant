# Responsible RAG Writing Assistant  
## Professional Project Plan

---

## 1. Product Framing

This project is a production-minded Generative AI application designed to demonstrate how **Retrieval-Augmented Generation (RAG)** can be operationalized responsibly in a professional setting.

The system assists users in generating tailored written documents (e.g. job applications) by grounding all generated output **exclusively in user-provided source materials**. Rather than treating the model as a black box, the application emphasizes transparency, traceability, and user control as first-class concerns.

The project is intentionally framed as an **internal enablement-style tool**, reflecting how GenAI solutions are typically deployed within enterprises: constrained, auditable, and designed to support human judgment rather than replace it.

---

## 2. Core Principles

The system is guided by the following non-negotiable principles:

1. **No model training or fine-tuning on user data**  
   User-provided documents are never used to modify or adapt the underlying language model.

2. **Retrieval-based grounding only**  
   All generated content must be explicitly grounded in retrieved source documents supplied by the user.

3. **Full transparency of sources**  
   Users must be able to inspect which documents and excerpts influenced each generated output.

4. **User-controlled data lifecycle**  
   Users retain control over ingestion, retention, and deletion of their data at all times.

5. **Enterprise-ready architecture and documentation**  
   The system is designed with clear boundaries, reproducibility, and maintainability in mind.

These principles take precedence over feature richness or automation.

---

## 3. High-Level Architecture

The system consists of the following major components:

- **Frontend:** A React-based single-page application focused on document editing and explainability.
- **Backend API:** A Python FastAPI service responsible for orchestration, validation, and business logic.
- **RAG Layer:** A LangChain-based retrieval and generation pipeline with explicit context injection.
- **Vector Database:** A local or managed vector store used for similarity search over embedded documents.
- **Infrastructure (optional):** Terraform-managed resources to demonstrate reproducible environments.

The architecture favors **explicit data flow** and **clear responsibility boundaries** over tightly coupled or opaque designs.

---

## 4. Functional Scope

The application supports three primary user workflows:

### Document Ingestion
Users upload personal documents (e.g. past job applications or CVs) and optionally enrich them with metadata such as role type, year, or skills. Documents are processed, chunked, embedded, and stored for later retrieval.

### Draft Generation (RAG)
Users provide a new input text (e.g. a job advertisement) along with generation preferences. The system retrieves relevant document fragments and generates a draft grounded solely in that retrieved context.

### Iterative Review
Users can inspect generated drafts, review associated sources and warnings, edit content manually, and regenerate specific sections as needed.

The system does not automate submission or decision-making; it supports drafting and review only.

---

## 5. Backend Design (Python + FastAPI)

The backend is structured around **clear service boundaries**, each with a single responsibility:

- **Ingestion Service:** Document processing, chunking, embedding, and metadata handling.
- **Retrieval Service:** Similarity search with metadata filtering and relevance thresholds.
- **Generation Service:** Prompt assembly, context injection, and structured output generation.
- **Validation / Warning Service:** Detection of over-reuse, unsupported claims, or low-confidence grounding.

API routing, business logic, and RAG logic are deliberately separated to ensure testability, maintainability, and ease of extension.

---

## 6. RAG Pipeline Design

Documents are chunked using a deterministic strategy and enriched with metadata before embedding. Metadata is preserved throughout the pipeline and used to constrain retrieval.

During generation:
- Only the top-K most relevant chunks are retrieved.
- Retrieved context is explicitly injected into the prompt.
- Prompt templates enforce strict grounding rules (“use only provided context”).

Model outputs are structured to include:
- Generated draft text
- Referenced sources
- Warnings or uncertainty indicators

If insufficient context is available, the system must surface this explicitly rather than hallucinate.

---

## 7. Frontend Design (React)

The frontend is designed as an **editorial interface**, not a conversational UI. It uses a clear three-panel layout:

1. **Draft Editor:** Displays generated content and supports user edits and section-level regeneration.
2. **Sources Panel:** Shows the documents and excerpts used during generation.
3. **Warnings Panel:** Surfaces confidence issues, over-reuse, or unsupported claims.

The UI prioritizes explainability and user control over automation. Generated content is always reviewable and editable.

---

## 8. Vector Database Strategy

For the MVP, a local **FAISS** vector store is used to maximize simplicity, debuggability, and transparency.

The abstraction layer is designed to support future migration to managed vector databases (e.g. Azure AI Search or OpenSearch) without requiring changes to retrieval logic or application flow.

---

## 9. Infrastructure as Code

Infrastructure is defined using **Terraform** to demonstrate reproducibility and professional DevOps practices.

Terraform modules may include:
- Backend API service
- Storage for documents and metadata
- Secrets management
- Optional managed vector database resources

Infrastructure is intentionally minimal in the MVP but structured for growth.

---

## 10. Security, Privacy, and Responsibility

The system implements safeguards appropriate for handling personal documents:

- Clear data ownership and isolation
- Configurable data retention and deletion
- Optional redaction hooks during ingestion
- Audit-friendly logging (excluding raw content)

The design explicitly avoids opaque prompt chaining, hidden memory, or uncontrolled reuse of personal data.

---

## 11. MVP Scope vs Future Work

### MVP Scope
- Single-user workflow
- Document ingestion and RAG-based draft generation
- Source transparency and warnings
- Local vector database

### Future Work (Out of Scope for MVP)
- Multi-user roles and access control
- Policy-driven configuration
- LangGraph-based multi-step workflows
- Cost tracking and usage analytics

These features are documented but intentionally deferred.

---

## 12. Application Summary Statement

> “I built a RAG-based AI writing assistant that helps users generate tailored documents by grounding generation in their own approved materials. The system emphasizes transparency, privacy, and reproducibility, and demonstrates how GenAI can be operationalized responsibly rather than treated as a black box.”

