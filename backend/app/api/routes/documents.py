"""Document management endpoints."""

from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ...core import DocumentNotFoundError, DocumentProcessingError, UnsupportedDocumentTypeError
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


@router.post("", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, or TXT)"),
    title: str | None = Form(default=None, description="Optional document title"),
    author: str | None = Form(default=None, description="Optional document author"),
) -> DocumentResponse:
    """Upload and ingest a document.

    Supported formats:
    - PDF (.pdf)
    - Word Document (.docx)
    - Plain Text (.txt)

    The document will be chunked and indexed for retrieval.
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
        document = await service.ingest_document(
            file=file.file,
            filename=file.filename,
            metadata=custom_metadata if custom_metadata else None,
        )

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
    except DocumentProcessingError as e:
        raise HTTPException(status_code=422, detail=e.message)


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
