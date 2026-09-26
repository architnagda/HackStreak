import os
import shutil
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.schemas.document import DocumentResponse, DocumentStats, DocumentChunkResponse
from app.api.deps import get_current_user
from app.services.document_parser import DocumentParser
from app.services.chunking_service import chunking_service
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

def process_document_pipeline(document_id: int, db_session: Session):
    """
    Synchronous / background pipeline execution for document parsing, chunking, and embedding.
    """
    doc = db_session.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return

    try:
        doc.status = DocumentStatus.PROCESSING.value
        db_session.commit()

        # Step 1: Parse Document
        pages_content = DocumentParser.parse_document(doc.file_path, doc.file_type)
        if not pages_content:
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = "No readable text content could be extracted from this document."
            db_session.commit()
            return

        total_pages = max([p.get("page_number", 1) for p in pages_content], default=1)
        doc.total_pages = total_pages

        # Step 2: Semantic Chunking
        raw_chunks = chunking_service.process_document_pages(pages_content)
        if not raw_chunks:
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = "Document text was empty after cleaning and chunking."
            db_session.commit()
            return

        # Step 3: Save chunks to MySQL
        db_chunks = []
        for rc in raw_chunks:
            chunk_obj = DocumentChunk(
                document_id=doc.id,
                chunk_index=rc["chunk_index"],
                page_number=rc["page_number"],
                section=rc.get("section"),
                content=rc["content"],
                token_count=rc.get("token_count", 0)
            )
            db_session.add(chunk_obj)
            db_chunks.append(chunk_obj)

        db_session.flush()  # assign IDs to chunk objects

        # Step 4: Generate Embeddings and Upsert to ChromaDB
        chunks_for_chroma = [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "page_number": c.page_number,
                "section": c.section,
                "content": c.content
            }
            for c in db_chunks
        ]
        embedding_service.add_chunks(
            document_id=doc.id,
            user_id=doc.user_id,
            filename=doc.filename,
            chunks=chunks_for_chroma
        )

        # Step 5: Mark Completed
        doc.total_chunks = len(db_chunks)
        doc.status = DocumentStatus.COMPLETED.value
        doc.error_message = None
        db_session.commit()
        logger.info(f"Successfully processed document {doc.id} ({doc.filename}): {doc.total_pages} pages, {doc.total_chunks} chunks.")

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
        db_session.rollback()
        doc = db_session.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = f"Processing error: {str(e)}"
            db_session.commit()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a document (PDF, Scanned PDF, JPG, PNG, DOCX), validates, parses, chunks, and indexes it.
    """
    filename = file.filename or "uploaded_file"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Ensure uploads directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    user_upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(user_upload_dir, exist_ok=True)

    # Unique stored file name to avoid collision
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    saved_file_path = os.path.join(user_upload_dir, unique_filename)

    # Read and save file
    contents = await file.read()
    file_size = len(contents)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of 50MB (got {file_size / (1024*1024):.1f}MB)."
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    with open(saved_file_path, "wb") as f:
        f.write(contents)

    # Create document record in MySQL
    doc = Document(
        user_id=current_user.id,
        filename=filename,
        file_path=saved_file_path,
        file_type=file.content_type or ext,
        file_size=file_size,
        status=DocumentStatus.UPLOADED.value,
        total_pages=0,
        total_chunks=0
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Run processing synchronously to guarantee immediate searchability
    process_document_pipeline(doc.id, db)
    db.refresh(doc)

    return doc


@router.get("", response_model=List[DocumentResponse])
def get_user_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all documents belonging to the authenticated user.
    """
    docs = db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.created_at.desc()).all()
    return docs


@router.get("/stats", response_model=DocumentStats)
def get_document_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns aggregated document metrics for the dashboard.
    """
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    total = len(docs)
    processing = sum(1 for d in docs if d.status in (DocumentStatus.PROCESSING.value, DocumentStatus.UPLOADED.value))
    completed = sum(1 for d in docs if d.status == DocumentStatus.COMPLETED.value)
    failed = sum(1 for d in docs if d.status == DocumentStatus.FAILED.value)

    return DocumentStats(
        total_documents=total,
        processing_documents=processing,
        completed_documents=completed,
        failed_documents=failed
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_by_id(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves single document details.
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes document record, on-disk file, chunks, and ChromaDB vector embeddings.
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # 1. Remove vector chunks from ChromaDB
    try:
        embedding_service.delete_document(doc.id)
    except Exception as e:
        logger.warning(f"Error deleting ChromaDB vectors for document {doc.id}: {e}")

    # 2. Remove physical file
    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception as e:
        logger.warning(f"Error removing physical file {doc.file_path}: {e}")

    # 3. Delete database record (cascades to document_chunks)
    db.delete(doc)
    db.commit()

    return {"message": f"Document '{doc.filename}' deleted successfully."}
