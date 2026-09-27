import os
import uuid
import shutil
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Document, DocumentChunk
from app.core.config import settings
from app.services.pdf_parser import DocumentParser
from app.services.chunker import RecursiveChunker
from app.services.embedding import embedding_service

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = logging.getLogger("smartdocs.api.documents")

def process_document_pipeline(document_id: str, file_path: str, chunk_size: int = None, chunk_overlap: int = None):
    """
    Background worker task: parses, chunks, generates embeddings, and saves into vector DB.
    """
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        doc.status = "processing"
        db.commit()

        # 1. Parse Document
        pages = DocumentParser.parse_file(file_path)
        if not pages:
            doc.status = "failed"
            doc.error_message = "Could not extract text from document (file may be empty or encrypted scanned image without OCR)."
            db.commit()
            return

        doc.page_count = len(pages)

        # 2. Chunk text
        chunker = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunk_data = chunker.chunk_document_pages(document_id, pages)

        if not chunk_data:
            doc.status = "failed"
            doc.error_message = "No semantic chunks generated."
            db.commit()
            return

        # 3. Generate Embeddings in batch
        texts_to_embed = [c["content"] for c in chunk_data]
        embeddings = embedding_service.get_embeddings(texts_to_embed)

        # 4. Save chunks to database
        db_chunks = []
        for i, c in enumerate(chunk_data):
            db_chunk = DocumentChunk(
                id=c["id"],
                document_id=document_id,
                chunk_index=c["chunk_index"],
                content=c["content"],
                page_number=c["page_number"],
                char_start=c["char_start"],
                char_end=c["char_end"],
                token_count=c["token_count"],
                embedding=embeddings[i],
                metadata_json=c["metadata"]
            )
            db_chunks.append(db_chunk)

        db.bulk_save_objects(db_chunks)
        doc.chunk_count = len(db_chunks)
        doc.status = "completed"
        db.commit()
        logger.info(f"Successfully processed document {doc.filename}: {len(db_chunks)} chunks indexed.")

    except Exception as e:
        logger.exception(f"Error processing document {document_id}: {e}")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "failed"
            doc.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    sync_processing: bool = False,
    db: Session = Depends(get_db)
):
    """
    Uploads a document (PDF, TXT, MD), initiates the RAG chunking & embedding pipeline.
    Optionally allows tuning chunk_size and chunk_overlap directly during upload!
    """
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = [".pdf", ".txt", ".md", ".csv", ".json", ".log"]
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed extensions: {', '.join(allowed_extensions)}"
        )

    doc_id = str(uuid.uuid4())
    safe_filename = f"{doc_id}_{file.filename}"
    saved_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(saved_path)

    # Create document record
    doc = Document(
        id=doc_id,
        filename=file.filename,
        file_type=ext,
        file_size=file_size,
        status="pending"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    if sync_processing:
        # Run synchronously (useful for tests or small uploads)
        process_document_pipeline(doc_id, saved_path, chunk_size, chunk_overlap)
        db.refresh(doc)
    else:
        # Run in background task
        background_tasks.add_task(
            process_document_pipeline,
            doc_id,
            saved_path,
            chunk_size,
            chunk_overlap
        )

    return {
        "message": "Document uploaded successfully and queued for ingestion.",
        "document": doc.to_dict()
    }


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    """Lists all uploaded documents with status and chunk count."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [d.to_dict() for d in docs]


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Retrieves document metadata along with its parsed chunks."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index).all()
    res = doc.to_dict()
    res["chunks"] = [c.to_dict() for c in chunks]
    return res


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Deletes a document and its associated chunks from the vector database."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(doc)
    db.commit()
    return {"message": f"Document '{doc.filename}' and its chunks deleted successfully."}
