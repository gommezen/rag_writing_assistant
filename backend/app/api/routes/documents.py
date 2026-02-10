"""Document management endpoints."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ...config import get_settings
from ...core import UnsupportedDocumentTypeError
from ...models import DocumentStatus, DocumentType
from ...services import get_ingestion_service

router = APIRouter(prefix="/documents", tags=["Documents"])


class DocumentResponse(BaseModel):
    """Response model for a document."""

    document_id: str
    filename: str
    document_type: str
    status: str
    metadata: dict[str, Any]
    chunk_count: int
    created_at: str
    updated_at: str
    error_message: str | None = None


class DocumentListResponse(BaseModel):
    """Response model for document list."""

    documents: list[DocumentResponse]
    total: int


class ChunkResponse(BaseModel):
    """Response model for a document chunk."""

    chunk_id: str
    chunk_index: int
    content: str
    page_number: int | None = None
    section_title: str | None = None


class DocumentChunksResponse(BaseModel):
    """Response model for document chunks."""

    document_id: str
    chunks: list[ChunkResponse]
    total_chunks: int


@router.post("", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, or TXT)"),
    title: str | None = Form(default=None, description="Optional document title"),
    author: str | None = Form(default=None, description="Optional document author"),
) -> DocumentResponse:
    """Upload and ingest a document (non-blocking).

    Supported formats:
    - PDF (.pdf)
    - Word Document (.docx)
    - Plain Text (.txt)

    Returns immediately with PENDING status. Poll GET /documents/{id}
    to check processing status. Document will be READY when indexing is complete.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    service = get_ingestion_service()

    # Build custom metadata
    custom_metadata = {}
    if title:
        custom_metadata["title"] = title
    if author:
        custom_metadata["author"] = author

    try:
        # Read file content into memory (fast)
        file_content = await file.read()

        # Create document record (fast, returns immediately)
        document = service.create_document_record(
            filename=file.filename,
            metadata=custom_metadata if custom_metadata else None,
        )

        # Schedule background processing (does not block)
        asyncio.create_task(service.process_document_background(document.document_id, file_content))

        # Return immediately with PENDING status
        return DocumentResponse(
            document_id=document.document_id,
            filename=document.filename,
            document_type=document.document_type.value,
            status=document.status.value,
            metadata=document.metadata.to_dict(),
            chunk_count=document.chunk_count,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
            error_message=document.error_message,
        )

    except UnsupportedDocumentTypeError as e:
        raise HTTPException(status_code=400, detail=e.message)


class UploadFromUrlRequest(BaseModel):
    """Request model for URL document ingestion."""

    url: str
    title: str | None = None


@router.post("/from-url", response_model=DocumentResponse)
async def upload_from_url(req: UploadFromUrlRequest) -> DocumentResponse:
    """Ingest a document from a URL (non-blocking).

    Fetches the webpage, extracts text content, chunks and indexes it.
    Returns immediately with PENDING status. Poll GET /documents/{id}
    to check processing status.
    """
    # Validate URL scheme
    from urllib.parse import urlparse

    parsed = urlparse(req.url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http and https URLs are supported")
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL")

    service = get_ingestion_service()

    try:
        document = service.create_url_document_record(
            url=req.url,
            title=req.title,
        )

        # Schedule background processing
        asyncio.create_task(service.process_url_background(document.document_id, req.url))

        return DocumentResponse(
            document_id=document.document_id,
            filename=document.filename,
            document_type=document.document_type.value,
            status=document.status.value,
            metadata=document.metadata.to_dict(),
            chunk_count=document.chunk_count,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
            error_message=document.error_message,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """List all uploaded documents."""
    service = get_ingestion_service()
    documents = service.list_documents()

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                document_id=doc.document_id,
                filename=doc.filename,
                document_type=doc.document_type.value,
                status=doc.status.value,
                metadata=doc.metadata.to_dict(),
                chunk_count=doc.chunk_count,
                created_at=doc.created_at.isoformat(),
                updated_at=doc.updated_at.isoformat(),
                error_message=doc.error_message,
            )
            for doc in documents
        ],
        total=len(documents),
    )


@router.get("/{document_id}/chunks", response_model=DocumentChunksResponse)
async def get_document_chunks(document_id: str) -> DocumentChunksResponse:
    """Get all chunks for a document, ordered by chunk_index.

    Returns the chunked content of a document for preview purposes.
    """
    service = get_ingestion_service()
    document = service.get_document(document_id)

    if document is None:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    # Get chunks from vector store
    chunks = service.get_document_chunks(document_id)

    return DocumentChunksResponse(
        document_id=document_id,
        chunks=[
            ChunkResponse(
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
            )
            for chunk in sorted(chunks, key=lambda c: c.chunk_index)
        ],
        total_chunks=len(chunks),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str) -> DocumentResponse:
    """Get a specific document by ID."""
    service = get_ingestion_service()
    document = service.get_document(document_id)

    if document is None:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    return DocumentResponse(
        document_id=document.document_id,
        filename=document.filename,
        document_type=document.document_type.value,
        status=document.status.value,
        metadata=document.metadata.to_dict(),
        chunk_count=document.chunk_count,
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
        error_message=document.error_message,
    )


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> dict:
    """Delete a document and its indexed chunks."""
    service = get_ingestion_service()
    deleted = service.delete_document(document_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    return {"status": "deleted", "document_id": document_id}


@router.post("/{document_id}/retry", response_model=DocumentResponse)
async def retry_document(document_id: str) -> DocumentResponse:
    """Retry processing a failed document.

    For file uploads: re-reads the saved file from data/uploads/.
    For URL documents: re-fetches from the stored URL.

    Args:
        document_id: ID of the failed document to retry

    Returns:
        Document with updated status (PENDING)
    """
    service = get_ingestion_service()
    document = service.get_document(document_id)

    if document is None:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    if document.status != DocumentStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry failed documents (current status: {document.status.value})",
        )

    # Reset document state
    document.status = DocumentStatus.PENDING
    document.error_message = None
    document.chunk_count = 0
    document.updated_at = datetime.now(UTC)
    service._save_document_registry()

    if document.document_type == DocumentType.URL:
        # URL document: re-fetch from stored URL
        url = (document.metadata.custom_metadata or {}).get("url")
        if not url:
            raise HTTPException(status_code=400, detail="URL not found in document metadata")
        asyncio.create_task(service.process_url_background(document.document_id, url))
    else:
        # File document: read from uploads directory
        settings = get_settings()
        upload_path = settings.uploads_dir / f"{document_id}{Path(document.filename).suffix}"

        if not upload_path.exists():
            document.status = DocumentStatus.FAILED
            document.error_message = "Original file not found. Please delete and re-upload."
            service._save_document_registry()
            raise HTTPException(
                status_code=400,
                detail="Original file not found. Please delete and re-upload the document.",
            )

        file_content = upload_path.read_bytes()
        asyncio.create_task(service.process_document_background(document.document_id, file_content))

    return DocumentResponse(
        document_id=document.document_id,
        filename=document.filename,
        document_type=document.document_type.value,
        status=document.status.value,
        metadata=document.metadata.to_dict(),
        chunk_count=document.chunk_count,
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
        error_message=document.error_message,
    )
